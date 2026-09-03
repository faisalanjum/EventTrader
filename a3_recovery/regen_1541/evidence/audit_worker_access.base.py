"""Machine audit v3: every drafting worker vs its EXACT three files, with
POSITIVE proof, an expected worker count, normalized paths, and empty = FAIL.

Usage:
  venv/bin/python harness/audit_worker_access.py <transcript_dir> [--expect N]

Rules (any breach = exit 1):
  - the folder must contain agent transcripts; EMPTY or missing = FAIL;
  - with --expect N, the transcript count must equal N exactly;
  - per worker: the assigned draft_inputs path is extracted from its OWN
    prompt (first user message); missing = FAIL;
  - per worker POSITIVE proof: it must have Read ALL THREE files — the
    wrapper, the item contract, and its assigned input (paths compared
    NORMALIZED via os.path.realpath — symlink/.. games cannot hide a file);
  - per worker: NO other Read target, and ANY Bash/Glob/Grep/other tool use
    (except StructuredOutput) is a violation outright — the official drafting
    agent type is Read-only, so these appearing at all means the wrong agent
    ran."""
import glob
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
WRAPPER = os.path.realpath(os.path.join(
    _HERE, "..", "keys", "K-fields", "drafting_wrapper.md"))
# STEP 3 REPOINT: the drafting worker receives the DRAFTER role prompt built
# by the one Step-2 builder. The retired contract card is deleted.
CONTRACT = os.path.realpath(os.path.join(_HERE, "exp5_prompt_drafter.md"))
_INPUT_RE = re.compile(r"(/[^\s]*?/keys/K-fields/draft_inputs/[^\s]+?\.json)")


def _norm(p):
    return os.path.realpath(p) if p else ""


def audit(d, expect=None):
    files = sorted(glob.glob(os.path.join(d, "agent-*.jsonl")))
    problems = 0
    if not files:
        print(f"FAIL: no agent transcripts in {d} — an empty audit is a "
              f"FAILURE, never a pass")
        return 1
    if expect is not None and len(files) != expect:
        print(f"FAIL: {len(files)} transcripts, expected EXACTLY {expect}")
        problems += 1
    for f in files:
        assigned, reads, extra = None, set(), []
        for line in open(f, encoding="utf-8", errors="replace"):
            try:
                j = json.loads(line)
            except Exception:
                continue
            msg = j.get("message") or {}
            content = msg.get("content")
            if assigned is None and msg.get("role") == "user":
                blob = content if isinstance(content, str) else json.dumps(content)
                m = _INPUT_RE.search(blob)
                if m:
                    assigned = _norm(m.group(1))
            for c in (content or []) if isinstance(content, list) else []:
                if not (isinstance(c, dict) and c.get("type") == "tool_use"):
                    continue
                name, inp = c.get("name", ""), c.get("input", {}) or {}
                if name == "Read":
                    path = _norm(str(inp.get("file_path") or ""))
                    if path in (WRAPPER, CONTRACT) or (assigned and
                                                       path == assigned):
                        reads.add(path)
                    else:
                        extra.append(f"Read(off-list): {path[:100]}")
                elif name == "StructuredOutput":
                    pass
                else:
                    extra.append(f"{name}(FORBIDDEN TOOL): {str(inp)[:80]}")
        missing = []
        if assigned is None:
            missing.append("no assigned input path found in the prompt")
        else:
            for label, req in (("wrapper", WRAPPER), ("contract", CONTRACT),
                               ("assigned input", assigned)):
                if req not in reads:
                    missing.append(f"never Read the {label}")
        if extra or missing:
            problems += 1
            print(f"VIOLATION {os.path.basename(f)} (assigned="
                  f"{os.path.basename(assigned) if assigned else None}):")
            for e in missing + extra[:8]:
                print(f"  {e}")
    print(f"workers audited: {len(files)}; expected: "
          f"{expect if expect is not None else 'n/a'}; problems: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    exp = None
    if "--expect" in args:
        i = args.index("--expect")
        exp = int(args[i + 1])
        del args[i:i + 2]
    sys.exit(audit(args[0], expect=exp))
