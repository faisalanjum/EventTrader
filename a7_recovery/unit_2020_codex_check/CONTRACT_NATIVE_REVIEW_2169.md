# New grading contract: actual connection proof

2026-09-15 UTC. No AI calls; no changed producer answer, key or score.

The existing correction preparation, capture, finalization, completion,
official grading consumer and scorer were exercised with the new contract.
The imported existing lifecycle suite uses explicit TEST replies, including
positive, negative, unresolved and tampered evidence. No consumer, matcher,
completion or scorer was replaced by a double.

Final attempt `unit_1957/logs/attempt_codex_contract2169_c`:
26 passed in 48.13s; pytest and wrapper both exit 0; stderr empty.
Started 04:29:11 UTC; recorded wrapper/PGID3994035, payload3994039; finished.
The exact command is CONTRACT_NATIVE_COMMAND_2169_C.sh.

| Artifact | SHA-256 |
|---|---|
| a7_grading_contract_2168.py | 23c36532b0629dc4a76a5ee34a0dcf9dbd9eaca6b8c3e57134d8a6b29fcaeba4 |
| test_grading_contract_native_2169.py | 52380f4b2a5b1ebfa2f67070f3d8ca8ef6d7191cdaab9500c1a1f579bcf82059 |
| run_grading_contract_native_2169.py | 5566f157b90cb81107663fd6029f966abd92807119d5b5d678e638646e9644d2 |
| map_contract_native_2169.tsv | 989693076d3acc1e4279fa65d6f9b6aa28273fe8aef62f775e5bb559ddd957b7 |
| attempt stdout.txt | 07e5343b6380dc6d6be076d9447fa74f88bc0817b21b94adc6299fe9be22921d |
| attempt stderr.txt | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| attempt exit | 9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa |

The map reuses the prior native fixture map, with four explicit current
correction-owner/test pins and the new contract/test added. Two test modules
not used by this run were removed from the new map only. All120 map rows
passed the existing boundary's validation. Old maps and files are unchanged.

Two earlier test-setup failures are preserved, not counted as product defects:
attempt a changed the identity-bearing TEST projects path while copying its
contents; the evidence validator correctly refused. Attempt b retained the
correct path but omitted the fixture's frozen output-token environment value;
preflight correctly refused. Attempt c uses the already documented fixture
environment unchanged. The test state builder gives new workflows identities
derived from this attempt's unique run directories; no real AI state is used.

This closes the new renderer -> existing preparer -> real completion ->
grading consumer connection. It does NOT close the affected live-question
frontier, later qualified judging, composition with earlier corrections,
final semantic review or publication. Core2169 still owns the independent
two-rule/materiality review; no new call is authorized yet.

Checklist: general rules/no example branches VERIFIED; single existing
preparer and scorer VERIFIED; new single-correction lifecycle VERIFIED;
minimality VERIFIED (no new scoring framework); focused/shared regression
262 tests +29 subtests and native26 tests PASS. Later correction composition
and final actual judgments remain explicitly open.
