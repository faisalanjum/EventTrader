# Preserve earlier verified corrections when applying a later one

2026-09-15 UTC. Required by the actual second instruction-correction round,
not hypothetical future support. No AI calls, new score formula or manual
judgment. The existing a7_grading_revision_2115.py remains byte-identical at
dd708431e2a106c4f711b89dfe8b9918a52ddf4f8616f5fefb94fa742783de76.

## Reproduction and smallest correction

Two pinned revisions each worked separately. Nesting their existing scopes
then failed: the earlier scope received the later revision's subset and
correctly refused it as a changed full population. The focused positive
control/reproducer failed once in0.13s before the adapter was added.

a7_grading_revision_chain_2169.py only dispatches the existing owner's two
reads: whole-base reads go through earlier verified revisions; the exact
current correction subset goes to the original native evidence consumer.
Any other request refuses. Each existing revision still checks its own full
producer/G1/population/source/input-version/root/completion identities and
applies its unchanged removal/replacement rule. Native evidence is never
converted into caller-supplied verdicts. Standard ExitStack callbacks restore
the consumer on all exits; no new dependency or generic patching layer.

The first adapter attempt incorrectly assumed the harness runner owned a
`_using` helper. Tests exposed that missing dependency. It was removed;
standard-library restoration now handles the one attribute directly.

## Actual checks

-17 focused tests pass in0.12s: both kinds across rounds, same-question
  ordering, partial/missing replacement without old credit, untouched fields,
  invalid/duplicate references, wrong code/owner/plan pins, in-scope edits,
  native refusal and unknown-subset refusal. Three actual composition mutants
  are caught using valid positive controls.
-Full affected regression:279 tests plus29 subtests pass in3.17s, exit0.
  Exact command: REVISION_CHAIN_REGRESSION_COMMAND_2169.sh.
-Existing native lifecycle plus two new multi-round scenarios:28 tests pass
  in53.84s; pytest and wrapper exit0. No consumer/completion/scorer double.
  Both rounds' changes reach the actual scorer; denominator/matches/park
  counts stay unchanged; a later partial result cannot recover the earlier
  aspect. All replies are explicit TEST evidence, not real model judgments.

Native attempt: unit_1957/logs/attempt_codex_revision_chain2169_a.
Started04:40:36UTC, wrapper/PGID4013669, payload4013673; finished exit0.
Command: REVISION_CHAIN_NATIVE_COMMAND_2169.sh.

| File | SHA-256 |
|---|---|
| a7_grading_revision_chain_2169.py | ba3175b8ed22ef52016c947fde09cb6c1c942ca8c427fe2ccf98ee755f06c2c1 |
| test_grading_revision_chain_2169.py | 584ba2e4801f100f0dd9fa693947dc0cadf0b70e2a2c98104575cb0e68dee828 |
| test_grading_revision_chain_native_2169.py | 45984c9d19f7404e35796679edf0129e9835302f001fbf70c3ae6a8bc9150d01 |
| map_revision_chain_native_2169.tsv | cf7f738323ec40da4c80f9a87d1940a4b185cbe473012db7762bfa495a1681f2 |
| run_grading_contract_native_2169.py | ed20c2e7ea5c2c73c0f49ee500609984e847f4c7b7751424994f50f6b914a9ee |
| native stdout.txt | 99b21e0ad9ebcefb724965e21cce2bb913601caf49ad9e9444e1e3067442b57b |
| native stderr.txt | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| native exit | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |

The earlier native caller5566f157 is preserved exactly under
snapshots_2169/run_grading_contract_native_2169.5566f157.py. The live caller
only gains a test-module choice, so one native runner serves both suites.

## Checklist / remaining limits

Generality: checked on unfamiliar TEST identities; no business strings or
model decisions in the adapter. Organization: the unchanged revision owner
and native consumer still own validation/replacement; this file owns order
only. Simplicity: no copied scorer, alternate completion loader or evidence
rewriter. Verification: test-first, negative/mutation and real native checks
above pass. Core's independent affected-question review, the live candidate
and exact later call ceiling, final-caller use of this sequence, new qualified
judgments, final cause report and publication remain open. This proves code
composition, not the correctness of future AI judgments or A7 PASS.
