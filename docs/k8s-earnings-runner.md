# Running Earnings Analysis from Kubernetes

This document explains how to run earnings-prediction and earnings-attribution from Kubernetes using the Claude Agent SDK.

## Prerequisites

1. **Claude Agent SDK installed** on K8s pod:
   ```bash
   pip install claude-agent-sdk
   ```

2. **ANTHROPIC_API_KEY** set as environment variable or K8s secret

3. **Working directory** mounted with access to:
   - `.claude/settings.json` (for MAX_THINKING_TOKENS)
   - `.claude/skills/` (skill definitions)
   - `earnings-analysis/` (output directory)

## Quick Start

### Option 1: Run directly from K8s pod

```bash
# Create a one-shot pod
kubectl run claude-earnings --rm -it \
  --image=python:3.11-slim \
  --env="ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" \
  -n claude-test \
  -- bash -c "
    pip install claude-agent-sdk && \
    cd /app && \
    python3 run-earnings.py
  "
```

### Option 2: Use the Python script

Create `run-earnings.py`:

```python
#!/usr/bin/env python3
"""
Run earnings prediction/attribution from K8s using Claude Agent SDK.

Usage:
    python3 run-earnings.py prediction TICKER ACCESSION
    python3 run-earnings.py attribution TICKER ACCESSION
"""
import asyncio
import sys
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_earnings(skill_type: str, ticker: str, accession: str):
    """Run earnings skill via Claude Agent SDK."""

    # IMPORTANT: Prompt must start with "Run /earnings-" for session detection
    prompt = f"""Run /earnings-{skill_type} for ticker {ticker}, accession {accession}.

Write your complete analysis to: earnings-analysis/Companies/{ticker}/{accession}.md

Include all analysis sections as specified in the skill.
Execute the mandatory thinking index build step at the end."""

    print(f'Starting earnings-{skill_type} for {ticker} ({accession})...')

    try:
        async for msg in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model='claude-opus-4-5-20251101',  # Required for extended thinking
                setting_sources=['user', 'project'],  # Load MAX_THINKING_TOKENS
                max_turns=50,  # Enough for full analysis
                permission_mode='bypassPermissions',  # No user prompts in K8s
            )
        ):
            print(f'  {type(msg).__name__}')

        print('Analysis complete!')
        return True

    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 run-earnings.py <prediction|attribution> <TICKER> <ACCESSION>")
        print("Example: python3 run-earnings.py prediction ALKS 0000950170-25-099382")
        sys.exit(1)

    skill_type = sys.argv[1]
    ticker = sys.argv[2]
    accession = sys.argv[3]

    if skill_type not in ['prediction', 'attribution']:
        print(f"Invalid skill type: {skill_type}. Use 'prediction' or 'attribution'")
        sys.exit(1)

    success = asyncio.run(run_earnings(skill_type, ticker, accession))
    sys.exit(0 if success else 1)
```

## Critical Settings

### ClaudeAgentOptions explained:

| Option | Value | Why |
|--------|-------|-----|
| `model` | `claude-opus-4-5-20251101` | Required for extended thinking |
| `setting_sources` | `['user', 'project']` | Loads MAX_THINKING_TOKENS from settings |
| `max_turns` | `50` | Enough for full multi-step analysis |
| `permission_mode` | `bypassPermissions` | No user prompts possible in K8s |

### Prompt Format (CRITICAL)

The prompt **MUST** start with `Run /earnings-prediction` or `Run /earnings-attribution` for the thinking index builder to find the session later.

**Good:**
```python
prompt = "Run /earnings-prediction for ticker ALKS, accession 0000950170-25-099382..."
```

**Bad (won't be found by thinking index builder):**
```python
prompt = "Analyze ALKS earnings for accession 0000950170-25-099382..."
```

## K8s Deployment Example

### ConfigMap for script

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: earnings-runner-script
  namespace: claude-test
data:
  run-earnings.py: |
    # ... paste the Python script above ...
```

### Job definition

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: earnings-prediction-alks
  namespace: claude-test
spec:
  template:
    spec:
      containers:
      - name: claude
        image: python:3.11-slim
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: anthropic-secret
              key: api-key
        command: ["bash", "-c"]
        args:
        - |
          pip install claude-agent-sdk
          cd /app
          python3 run-earnings.py prediction ALKS 0000950170-25-099382
        volumeMounts:
        - name: workdir
          mountPath: /app
        - name: script
          mountPath: /app/run-earnings.py
          subPath: run-earnings.py
      volumes:
      - name: workdir
        hostPath:
          path: /home/faisal/EventMarketDB
      - name: script
        configMap:
          name: earnings-runner-script
      restartPolicy: Never
  backoffLimit: 1
```

## Output Locations

| Output | Location |
|--------|----------|
| Analysis report | `earnings-analysis/Companies/{TICKER}/{accession}.md` |
| Predictions CSV | `earnings-analysis/predictions.csv` |
| Session transcript | `~/.claude/projects/-home-faisal-EventMarketDB/{sessionId}.jsonl` |
| Agent files (v2.1.1) | `~/.claude/projects/-home-faisal-EventMarketDB/agent-*.jsonl` |
| Agent files (v2.1.3+) | `~/.claude/projects/-home-faisal-EventMarketDB/{sessionId}/subagents/` |
| Thinking index | `~/Obsidian/EventTrader/Earnings/earnings-analysis/thinking/` |

## Timing

K8s runs typically take **15-20 minutes** vs **3-5 minutes** locally. This is because:

1. **No prompt caching**: Each K8s run starts fresh with no cached context
2. **Full skill chain**: earnings-prediction → filtered-data → neo4j-* → perplexity-*
3. **Extended thinking**: Opus with MAX_THINKING_TOKENS generates more reasoning
4. **API latency**: K8s pod may have higher network latency to Anthropic API

## Troubleshooting

### Session not found by thinking index builder

**Symptom**: `build-thinking-index.py` reports "No sessions found"

**Cause**: Prompt doesn't match expected pattern

**Fix**: Ensure prompt starts with `Run /earnings-prediction` or `Run /earnings-attribution`

### Missing thinking blocks

**Symptom**: Thinking file has few/no blocks

**Cause**: Wrong model or missing settings

**Fix**: Verify `model='claude-opus-4-5-20251101'` and `setting_sources=['user', 'project']`

### Permission errors

**Symptom**: "I need permission to..." messages

**Cause**: Missing `permission_mode='bypassPermissions'`

**Fix**: Add to ClaudeAgentOptions

---

*Last updated: 2026-01-16*
