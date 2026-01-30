# Driver Field Improvement Plan

## Problem

Driver field is critical - entire infrastructure depends on it being correct. Current "5-15 words" is too terse for full context.

## Changes (Minimal)

### 1. Upgrade Models

| Agent | Current | New | Why |
|-------|---------|-----|-----|
| bz-news-driver | haiku | **opus** | Nuanced analysis of news→move causation - accuracy critical |
| external-news-driver | sonnet | sonnet | Already adequate for web research |

**Note:** Using opus for bz-news-driver since accuracy is critical and it's the primary analysis path.

### 2. Expand Driver Field

**From:** "5-15 words explaining move"

**To:** "1-3 sentences covering":
- **What**: The specific event/news (e.g., "Q4 earnings beat with EPS $2.10 vs $1.95 expected")
- **Why it moved the stock**: Causation logic (e.g., "signaling demand recovery after 3 quarters of decline")
- **Context**: Why this matters now (e.g., "first beat since iPhone 15 launch concerns")

**Format:** Single field, semicolon-separated if multiple drivers. No bullet points.

**Example transformation:**
```
# Before (too terse)
"Q4 earnings beat expectations"

# After (full context)
"Q4 EPS $2.10 beat $1.95 consensus by 8%; iPhone revenue +6% YoY reversed 3-quarter decline; Services hit record $23B suggesting successful diversification"
```

### 3. Add Reasoning Instruction

Add to both agents before output step:

```markdown
### Analysis (Internal - Do Not Output)

Before generating driver, answer:
1. What EXACTLY happened? (specific numbers, not vague)
2. Why would this move the stock in THIS direction?
3. Does magnitude make sense? (5% move needs 5%-worthy news)
4. Is this the PRIMARY driver or a symptom?
5. Any doubt? → external_research=true
```

### 4. Confidence Calibration

Tighten confidence rules:

| Scenario | Confidence |
|----------|------------|
| Clear causation + direction match + magnitude justified | 80-95 |
| Clear causation but magnitude seems off | 50-70 |
| Correlation but causation uncertain | 30-50 |
| News exists but doesn't explain move | 10-30 + external_research=true |
| No relevant news | 0 + external_research=true |

## Files to Update

1. `.claude/agents/bz-news-driver.md`
   - Change `model: haiku` → `model: sonnet`
   - Expand driver instructions
   - Add reasoning step

2. `.claude/agents/external-news-driver.md`
   - Expand driver instructions
   - Add reasoning step

3. `.claude/skills/earnings-orchestrator/SKILL.md`
   - Update driver field description in output format

4. `.claude/skills/news-impact/SKILL.md`
   - Update driver field description

## Cost Impact

- bz-news-driver: ~3x cost increase (haiku → sonnet)
- Per ticker with ~10 significant dates: ~$0.02 → ~$0.06
- Acceptable for accuracy gains

## Not Doing (Overkill)

- Opus 4.5 for every call (too expensive)
- Structured multi-field output (adds complexity)
- Verification agent (adds latency)
- LLM-as-judge validation (diminishing returns)

## Implementation Order

1. Update bz-news-driver.md (model + instructions)
2. Update external-news-driver.md (instructions only)
3. Test with one ticker
4. Update skill docs for consistency
