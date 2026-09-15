# Correct the earlier null-change task selection

2026-09-15 UTC. Root review data, not new judgments or call authorization.
FINAL_DESIGN7.1 expressly leaves change_value null when it can merely be
derived from the closed operands. The renderer32e2f650 adds that statement to
the old contract. G2_MATERIALITY_REVIEW_2159 selected six closed-operand rows
that already supplied a change, but did not include affected rows that OMIT
it. An omitted field is still an assertion; this was my selection error.

Concrete finding: M6d9dd25a44c4125e, P1/0000940944-26-000009 gold1/produced2,
is still carried from the old prompt. It stores2.68 and2.74, null change,
prior_year and Q3FY2026; the source quotes a2.2% decrease. The current key's
source-only review expressly calls the null change lawful. The old prompt
does not contain the corrected null/read-time sentence. This is a changed
grading task, not permission to manually turn its negative verdict positive.

The complete228-carried inventory has37 questions/22 distinct full records
with both stored closed operands. I read all22 records, quantities, units,
source quotes and scopes.23 questions explicitly quote a change of the SAME
claim and need the already-approved corrected instruction;14 do not state a
numeric delta for their claim and remain unchanged. The latter include a
multi-row table whose percent changes belong to other claims, so this is not
a quote-keyword classifier. The JSON lists every one of the37 exact identities,
full records,23 selected questions and14 exclusions. The remaining191 do not
have both stored closed operands; Core must independently check the class
boundary and source/rule reasoning before I freeze the final call list.

No new prompt is proposed: contract23c36532 already includes renderer32e's
null-change sentence. All current G3 judgments already received it. The
additional selection concerns only carried G2 tasks, includes prior positive
and negative results alike, and must join the two-clause frontier without
duplicates. Existing82/116 corrections stay first; any new correction is a
later pinned revision. No changed score or assumed improvement is claimed.

Pending: independent Core review; exact combined selection, native preparation,
full script fit/call ceiling; approved new grading replies and final scoring.
