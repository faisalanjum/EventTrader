# A7 model reuse: offline check and exact remaining boundary

Codex, 2026-09-15 UTC. This is an offline setup review, not a Qwen run,
transport qualification, A7 PASS, or permission to activate another model.
The current Sonnet answers, prompts, key, launcher and grades are unchanged.

## Conclusion

The existing parser, reader, no-write route and scorer can be reused. A new
model does NOT need a second grader. However, changing only a model name is
NOT currently a verified end-to-end launch path. The frozen Sonnet launcher
and its subscription evidence cannot be relabelled as local-model evidence.
The owner's separate host-side task must finish the local transport boundary
below before a real local experiment can be admitted.

No inference engine, client, server, preflight, settings, production component
or current experiment owner was changed. No network or model call occurred.
The only new executable file is test_model_reuse_offline_2176.py.

## Authorities and owners actually inspected

Read completely: QwenInference.md (776 lines), LOCAL_QWEN_HANDOFF.md (97),
config/local_llm.py (388), promptStandard.md (116). Also read the live Steps
model-neutral and first-release rules and work-order section6. QwenInference
explicitly retires the older handoff's model, capacity, concurrency, structured
call and run_qwen/preflight advice. Do not combine the two recipes.

Exact main authorities, under .claude/plans/Drivers/FinalDesign:

- LeftOverSteps/QwenInference.md:
  db6f762be5e73c4fef2ad3996e2c444a1fc77fd10314c1d4765f0aa6da9cfb47.
- QwenTests/LOCAL_QWEN_HANDOFF.md:
  4a9154d9d39cc8f205e3fff5042560b750a7bab10154a53a58ca104dff5e6c38.
- LeftOverSteps/Steps.md:
  0ce8143ba06598dd9b9f566e3f9f271b73accad1515043bc187537e6fbfd4140.
- LeftOverSteps/promptStandard.md:
  1b2222f3d241d953e50718b5bf9a1adcd60ce1e8dc83411e73fa49561473f92d.

Main and recovery config/local_llm.py are identical:
836e5722ec01c5e1ef53b8eeb2675beb4fcb58d9e10b22570afc3c00daf80b66.
Its selected model is environment-controlled; its recorded default is
qwen3.8:27b-mlx, not proof of what is resident on the remote host.

Shared recovery owners used by the offline proof:

- grader_20260909/harness_g1v3/raw_transport.py:
  4d51412261aa9a496ca9a0c85d62547152f841e05a2b6fc484aa66af9e07ba0a.
- grader_20260909/harness_g1v3/a1_reader.py:
  98055e556fdb0324c022f8f14db5ec463b4486914df48bda72b6c519e731e649.
- unit_2008/harness_g1v3/scorers/score_exp5_current.py:
  6d0a02285162a079a81615db6ae64fddaa43acef64214315339c8d78bfd7f43e.

The actual saved score uses the same scorer plus its already verified
duplicate-accounting correction, with unchanged native completion, grading
revision and input owners. FINAL_SCORE_FINDINGS_2174.md identifies that run.
This setup check introduces none of those rules a second time.

## What the offline tests actually prove

Focused command: the existing boundary.py --host map_current_key_2148.tsv,
then pytest -q -p no:cacheprovider test_model_reuse_offline_2176.py, with
PYTHONDONTWRITEBYTECODE=1. Result:15 passed in0.26s, raw exit0.

| Boundary | Actual evidence |
|---|---|
| Raw generation and capture | Two explicit mocked runtime names receive identical frozen system/user text and settings; exactly one transport attempt. Whitespace, Unicode and a negative high-precision decimal survive raw capture and the shared parser. Existing capture refuses overwrite. |
| Invalid replies | All seven malformed/duplicate/nonfinite/trailing-text cases are saved intact and then refused by the same parser, with a legal positive control. |
| Reader through scoring | An unfamiliar synthetic event goes through raw capture, real A1 normalization/validation, the real public no-write route and the actual scorer. Independent fixture key:1 required fact,1 match,recall1.0. Supplied all-true TEST verdicts pass; absent judgments stay incomplete; one false TEST verdict fails. This is deterministic integration evidence, NOT actual AI accuracy. |
| Identity and schema | Wrong source and extra schema fields refuse. Each of the10 existing identity fields is tested both changed and missing, alongside a matching unfamiliar frozen-model identity. This is not a fabricated local workflow receipt or a complete local resume proof. |
| Retry control | Explicit retries=0 makes exactly one failed transport attempt. No model answer is regenerated. |
| Known local limitations | Mocked truncated output returns with a flag; a changed returned model is lost from stats; an oversized prompt reaches the transport stub; a stream without a final completion marker returns parseable text with no done_reason. These passing tests CONFIRM limitations, not launch readiness. |

## The one later local-transport task, not another grading project

1. Freeze one separately authorized runtime and its exact model/digest,
   engine/version, transport, reasoning, schema behavior and settings. Use
   config/local_llm.py only. Keep one model for the new run; do not change or
   relabel this Sonnet run. Do not let the answer-producing call grade itself.
2. Measure the exact final prompt/system bytes with the actual host model's
   tokenizer/template and output allowance. Prove a sufficient pre-call size
   guard before launch. The client has no such guard: its MLX input check is
   disabled, and the GGUF check is after the response. The ledger's25,000
   conservative token limit is not a measurement of these prompts. Never
   trim, split or rewrite a frozen input to make it fit; count it unserved.
3. Use only the documented raw L.generate path, sequentially, with all
   settings explicit and retries=0. No structured(), prompt additions, format
   repair, hidden retry, provider fallback or inference-engine change here.
   Save original response text and sufficient actual returned identity and
   termination evidence before interpretation. The current stats omit model
   and completion metadata; merely recording the requested model is not
   evidence of the model that replied. Interrupted raw data must not vanish.
4. Bind each new attempt to its frozen packet, input, prompt, runtime and raw
   evidence; require real completion, no truncation and exact provenance.
   Missing/invalid/refused/unserved items stay in accounting. Reuse completed
   answers only under the same full bindings, not case ID alone. The current
   subscription workflow receipt is not an Ollama receipt: this connection
   still needs honest transport evidence and a focused positive/drift/resume
   test on the host. Never forge a subscription transcript or bypass the
   existing completion gate to make a local response fit.
5. Feed admitted raw replies into the SAME existing parser, normalization,
   schema/source checks, independent grading, no-write route, accounting and
   scorer. Reuse sources and the approved key wherever their bindings still
   hold. New produced answers need their own matching/meaning judgments;
   Sonnet's old verdicts cannot be attached to different model answers.

The minimal missing work is capacity/identity/completion capture and the thin
connection to existing run evidence, not a scoring rewrite. The required
host measurements and receipt connection are UNVERIFIED and have no promised
duration. Do not claim local drop-in readiness or start a live probe here.

## Final checklist for this bounded pass

- Generality VERIFIED: no model-name decision in shared reader/scorer; fixed
  Sonnet identifiers in the frozen A2/A5 run are legitimate provenance, not
  strings to replace. No generic provider framework or semantic word list.
- Workflow VERIFIED OFFLINE, with the local launch/evidence limits above.
- Duplication/organization VERIFIED: existing owners reused; one new test
  file and this review, no second parser, validator, client or scorer.
- Simplicity VERIFIED: no runtime abstraction or configuration was added.
- Testing VERIFIED for the stated15 offline checks; full affected regression
  is recorded in FINAL_CHECKPOINT_REVIEW_2176.md. No live local test, model
  qualification, production qualification or universal reliability claim.

Production does not import this experiment harness. It may reuse the later
approved contracts/evidence under the roadmap; the grader remains an external
evaluation tool. A7's observed FAIL and unresolved judgments remain unchanged.
