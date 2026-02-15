#!/usr/bin/env python3
"""Lint data sub-agents (§10.6 of DataSubAgents.md).

Rules: R1 evidence-standards | R2 no wildcard matchers | R3 PIT-DONE compliance
       R5 file paths exist | R6 $CLAUDE_PROJECT_DIR in hooks | R7 no deprecated skills
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = ROOT / ".claude" / "agents"
SKILLS_DIR = ROOT / ".claude" / "skills"
AGENT_GLOBS = ["neo4j-*.md", "bz-news-api.md", "perplexity-*.md", "alphavantage-*.md"]

PIT_DONE = {
    "neo4j-news": {
        "skills": ["pit-envelope"],
        "pre": ["mcp__neo4j-cypher__write_neo4j_cypher"],
        "post": ["mcp__neo4j-cypher__read_neo4j_cypher"],
    },
    "neo4j-vector-search": {
        "skills": ["pit-envelope"],
        "pre": ["mcp__neo4j-cypher__write_neo4j_cypher"],
        "post": ["mcp__neo4j-cypher__read_neo4j_cypher"],
    },
    "bz-news-api": {
        "skills": ["pit-envelope"],
        "pre": [],
        "post": ["Bash"],
    },
}
DEPRECATED_SKILLS = {"filtered-data"}
PATH_RE = re.compile(r"(?:\$CLAUDE_PROJECT_DIR/)?((?:\.claude|scripts)/[\w/._-]+\.\w+)")


def discover():
    agents = []
    for g in AGENT_GLOBS:
        agents.extend(AGENTS_DIR.glob(g))
    return sorted(set(agents))


def parse(path: Path) -> dict:
    text = path.read_text()
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {"name": path.stem, "skills": [], "body": text, "path": path,
                "pre_matchers": [], "post_matchers": [], "post_commands": [],
                "all_matchers": [], "all_commands": []}
    fm, body = parts[1], parts[2]
    nm = re.search(r"^name:\s*(.+)", fm, re.M)
    name = nm.group(1).strip().strip('"') if nm else path.stem
    sm = re.search(r"^skills:\n((?:\s+- .+\n)+)", fm, re.M)
    skills = [s.strip().strip('"') for s in re.findall(r"-\s+(.+)", sm.group(1))] if sm else []

    pre_text = post_text = ""
    if "PreToolUse:" in fm and "PostToolUse:" in fm:
        pre_text = fm[fm.index("PreToolUse:"):fm.index("PostToolUse:")]
        post_text = fm[fm.index("PostToolUse:"):]
    elif "PreToolUse:" in fm:
        pre_text = fm[fm.index("PreToolUse:"):]
    elif "PostToolUse:" in fm:
        post_text = fm[fm.index("PostToolUse:"):]

    return {
        "name": name, "skills": skills, "body": body, "path": path,
        "pre_matchers": re.findall(r'matcher:\s*"([^"]*)"', pre_text),
        "post_matchers": re.findall(r'matcher:\s*"([^"]*)"', post_text),
        "post_commands": re.findall(r'command:\s*"([^"]*)"', post_text),
        "all_matchers": re.findall(r'matcher:\s*"([^"]*)"', fm),
        "all_commands": re.findall(r'command:\s*"([^"]*)"', fm),
    }


def check_paths(text: str, label: str) -> list[str]:
    errors, seen = [], set()
    for m in PATH_RE.finditer(text):
        rel = m.group(1)
        if rel not in seen:
            seen.add(rel)
            if not (ROOT / rel).exists():
                errors.append(f"ERROR [R5] {label}: path '{rel}' not found")
    return errors


def lint(agent: dict) -> list[str]:
    errs = []
    name, rel = agent["name"], agent["path"].relative_to(ROOT)

    # R1
    if "evidence-standards" not in agent["skills"]:
        errs.append(f"ERROR [R1] {rel}: missing 'evidence-standards' in skills")
    # R2
    for m in agent["all_matchers"]:
        if m in ("*", ".*", ""):
            errs.append(f"ERROR [R2] {rel}: wildcard matcher '{m}'")
    # R3
    if name in PIT_DONE:
        spec = PIT_DONE[name]
        for s in spec["skills"]:
            if s not in agent["skills"]:
                errs.append(f"ERROR [R3] {rel}: missing skill '{s}'")
        for pm in spec["pre"]:
            if pm not in agent["pre_matchers"]:
                errs.append(f"ERROR [R3] {rel}: missing PreToolUse matcher '{pm}'")
        for pm in spec["post"]:
            if pm not in agent["post_matchers"]:
                errs.append(f"ERROR [R3] {rel}: missing PostToolUse matcher '{pm}'")
        if not any("pit_gate.py" in c for c in agent["post_commands"]):
            errs.append(f"ERROR [R3] {rel}: PostToolUse must reference pit_gate.py")
    # R5 (agent body)
    errs.extend(check_paths(agent["body"], str(rel)))
    # R6
    for cmd in agent["all_commands"]:
        if cmd.strip().startswith("echo "):
            continue
        for pm in re.finditer(r"(?:\.claude|scripts)/", cmd):
            pos = pm.start()
            prefix = "$CLAUDE_PROJECT_DIR/"
            if pos < len(prefix) or cmd[pos - len(prefix):pos] != prefix:
                errs.append(f"ERROR [R6] {rel}: hook needs $CLAUDE_PROJECT_DIR: '{cmd}'")
                break
    # R7
    for s in agent["skills"]:
        if s in DEPRECATED_SKILLS:
            errs.append(f"ERROR [R7] {rel}: deprecated skill '{s}'")
    return errs


def main():
    agents_paths = discover()
    if not agents_paths:
        print("No data agents found")
        sys.exit(1)

    agents = [parse(p) for p in agents_paths]
    errors = []
    for a in agents:
        errors.extend(lint(a))

    # R5 on skill files (each skill checked once)
    checked_skills = set()
    for a in agents:
        for sk in a["skills"]:
            if sk not in checked_skills:
                checked_skills.add(sk)
                sp = SKILLS_DIR / sk / "SKILL.md"
                if sp.exists():
                    errors.extend(check_paths(sp.read_text(), f"skill:{sk}"))

    for e in errors:
        print(e)
    status = "FAIL" if errors else "PASS"
    print(f"\n{status} | {len(errors)} errors | {len(agents)} agents checked")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
