# QF-01 local-Qwen table test report

## Bottom line

**Qwen did not pass this task.**

| Strict measure | Result |
|---|---:|
| Complete correct answers | 0 / 93 |
| Wrong answers | 92 / 93 |
| Invalid answers | 1 / 93 |
| Precision | 0% |
| Recall | 0% |
| Decision | `NOT_SAFE_FOR_TASK` |

This is a screen of 93 requests from only 8 independent tables. It is not a
general production certification.

## What the zero means

The zero is mechanically correct, but it does **not** mean Qwen understood
nothing. Every valid answer failed at least one required field, and the
period-header field failed in every case.

| Exact field | Correct |
|---|---:|
| Request ID | 92 / 93 |
| Anchor ID | 92 / 93 |
| Row block | 89 / 93 |
| Full occurrence ID | 77 / 93 |
| Printed label | 87 / 93 |
| Exact period-header array | **0 / 93** |

Seventy-two answers reached the final period-header check with every earlier
field correct. One answer ran to the frozen 512-token output cap and was
counted invalid without a retry.

## Why the input shape hurt

The failure is partly Qwen and partly the test interface:

1. Occurrence markers split the source headers. For example, Qwen saw
   `4⟨long-id⟩Q24`, while the hidden answer required `4Q24`.
2. The flattened table did not explicitly attach each cell to its complete
   header path. Qwen had to reconstruct quarter-versus-year alignment.
3. The instruction called table-wide scale text a “column-header line” only
   indirectly. Qwen omitted `(in millions)` in 23 of the 24 answers that
   required it; in 10 cases that was the only period error.
4. Qwen sometimes recomposed headers instead of copying them, such as
   `Q24 2024` instead of `4Q24`.
5. Long identifier copying created five avoidable format failures. If code
   built the full ID from Qwen’s selected row and occurrence number, exact
   cell selection would rise from 77/93 to 82/93—but still remain below the
   required 93/93.

Therefore, the wrapper clearly needs simplification, but Qwen also made real
row/cell selection errors. The result cannot be rescued into a pass.

## Honest run record

- Model: `qwen3.6:35b-a3b`, GGUF `Q4_K_M`
- Model digest: `07d35212591fc27746f0a317c975a6d68754fb38e9053d82e25f06057af28522`
- Ollama: `0.32.3`
- Reasoning off; temperature zero; no completed-answer retries
- 93 separate stateless calls; four concurrent workers
- 43 minutes 31 seconds; 1,004,082 input tokens; 17,114 output tokens
- Zero input truncations; one output truncation
- Model fingerprint unchanged before and after

An earlier run was stopped unscored when the input guard caught a too-small
context. Its bytes and reason are preserved under `results/aborted_run_1/`.
No hidden answer was opened before the valid run finished.

## Smallest correct next design

Do not rerun these 93 cases as a new certification. They are now a development
set because their hidden answers have been opened.

For a new unseen set, split the work:

1. Code presents clean candidate rows and precomputed header paths for **all**
   candidates.
2. Qwen returns only a small candidate number and occurrence number, or
   abstains.
3. Code constructs the long IDs and copies the exact label and headers from
   source; Qwen never retypes them.
4. Test true abstention separately.
5. Require a fresh exact 100% result before any Qwen role is approved.

This tests the real judgment—choosing the correct cell—without charging Qwen
for deterministic copying that code can guarantee.
