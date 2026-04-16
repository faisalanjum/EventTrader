---
name: test-all-datasubagents-fork
description: Validate that a forked skill can invoke the full original data-subagent surface and record per-agent results.
context: fork
model: opus
effort: high
allowed-tools: Read, Write, Skill
skills:
  - neo4j-report
  - neo4j-transcript
  - neo4j-xbrl
  - neo4j-entity
  - neo4j-news
  - neo4j-vector-search
  - alphavantage-earnings
  - yahoo-earnings
  - bz-news-api
  - perplexity-search
  - perplexity-ask
  - perplexity-reason
  - perplexity-research
  - perplexity-sec
---

Validate whether this forked skill can invoke the complete original data-subagent surface.

Write the final report to:
`earnings-analysis/test-outputs/test-all-datasubagents-fork.json`

Also write a short human-readable summary to:
`earnings-analysis/test-outputs/test-all-datasubagents-fork.txt`

Rules:
1. Test every command below exactly once.
2. Use the slash command form directly, e.g. `/neo4j-report`.
3. For each command, classify:
   - `invoke_ok`: the slash command resolved and returned either data, a structured gap, or a provider/source error originating inside that subagent.
   - `invoke_failed`: the slash command was unavailable, could not be called from this forked skill, or failed before reaching the subagent itself.
4. Keep evidence short: one compact snippet per result.
5. Do not stop early if one command fails.
6. Final output must be valid JSON.

Use these test prompts:

1. `/neo4j-report`
Prompt: `Get one recent AAPL 8-K earnings filing. Return only the smallest useful result.`

2. `/neo4j-transcript`
Prompt: `Get one recent AAPL earnings call Q&A exchange. Return only the smallest useful result.`

3. `/neo4j-xbrl`
Prompt: `Get one recent AAPL revenue XBRL fact. Return only the smallest useful result.`

4. `/neo4j-entity`
Prompt: `Get AAPL company name and sector. Return only the smallest useful result.`

5. `/neo4j-news`
Prompt: `Get one recent AAPL earnings-related headline. Return only the smallest useful result.`

6. `/neo4j-vector-search`
Prompt: `Find one semantically relevant AAPL earnings-related news or transcript match. Return only the smallest useful result.`

7. `/alphavantage-earnings`
Prompt: `Get AAPL quarterly earnings actuals in open mode. Return only one recent item.`

8. `/yahoo-earnings`
Prompt: `Get one recent AAPL earnings or analyst-upgrade item. Return only the smallest useful result.`

9. `/bz-news-api`
Prompt: `Get one recent AAPL Benzinga news item. Return only the smallest useful result.`

10. `/perplexity-search`
Prompt: `Search for AAPL latest earnings transcript date. Return only the smallest useful result.`

11. `/perplexity-ask`
Prompt: `What was AAPL latest quarterly EPS versus consensus?`

12. `/perplexity-reason`
Prompt: `Why did AAPL stock react to its most recent earnings? Keep it brief.`

13. `/perplexity-research`
Prompt: `Research one concise fact about AAPL's most recent earnings reaction. Keep it minimal.`

14. `/perplexity-sec`
Prompt: `Find one recent AAPL 10-Q or 8-K filing URL from EDGAR. Return only the smallest useful result.`

Output JSON shape:

```json
{
  "test_name": "test-all-datasubagents-fork",
  "from_skill_context": true,
  "results": [
    {
      "name": "neo4j-report",
      "invocation_status": "invoke_ok",
      "outcome_type": "data | gap | provider_error | invoke_failed",
      "evidence": "short snippet"
    }
  ],
  "summary": {
    "total": 14,
    "invoke_ok_count": 0,
    "invoke_failed_count": 0
  }
}
```

For `outcome_type`:
- `data`: returned usable data
- `gap`: subagent ran but returned a gap/no-data outcome
- `provider_error`: subagent ran but the upstream source/auth/provider failed
- `invoke_failed`: slash command unavailable or call path itself failed
