Copied from Faisal's Mac on 15 Nov 2026 (America/Toronto, EST) by Claude Code, for Codex.
- reviews.json: the three independent reviews (lenses: official-docs, record-coverage, minimalism). Each has
  "findings" (topic, applies_to codex|draft|both, verdict, evidence, recommendation, impact) and "bottom_line".
  They reviewed brief.md (Codex's earlier summary plan and Claude's "value-first" draft), not Codex's later detailed plan.
- brief.md: what the reviewers were given (requirements, measured results, both plans, paths on the Mac).
- locate_boundaries.py: the "56 of 60" Locate test (52 short sentences, 60 expected spans: percentages, dollar
  amounts, dates, people, companies, places; plus missing-fact cases, the 10 eval Locate requests and a 1,028-word report).
- locate_before.json / locate_after.json: results before / after the 15 Nov Locate punctuation fix
  (45 -> 56 of 60; numbers 28/28 after; the 4 misses are names: "Contoso", "Toronto", two names after Dr./Ms.).
- USAGE.md: the Mac Decider's usage guide, including the punctuation-fix note.
