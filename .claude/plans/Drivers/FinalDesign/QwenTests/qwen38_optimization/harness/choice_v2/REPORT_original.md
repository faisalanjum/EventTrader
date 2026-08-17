# QF-01 choice-v2 development result

## Verdict

**NOT PERFECT — do not use Qwen alone for this task.**

| Result | Count |
|---|---:|
| Correct exact cell | 75 |
| Wrong exact cell | 18 |
| Abstained | 0 |
| Invalid | 0 |
| Total | 93 |

Precision = recall = **75/93 = 80.65%**.

## What the redesign proved

- Every prompt was built by plain code from real HTML.
- The hidden key did not build or alter any prompt.
- Qwen returned only `{"choice": number-or-null}`.
- Code copied every ID, label, value, and header.
- All 93 first completed answers were valid, untruncated, and unretried.

The original copying and formatting failures were therefore removed.

## The 18 wrong choices

- **11** chose the correct row but the wrong left-to-right occurrence.
- **7** chose the wrong row:
  - six selected `Gas Sales` instead of `Gas Revenues`;
  - one selected bauxite shipments instead of alumina shipments.

The 11 occurrence errors are still avoidable mechanical work: the request
already supplies the occurrence number, so code can apply it after a row is
selected. On row choice alone, Qwen was **86/93 = 92.47%**, still below the
required 100%.

## Important development finding

A small source-only lexical probe devised after scoring uniquely found the
correct row in all 93 opened cases: exact normalized row-label match first,
otherwise all known-label words must occur in the row plus its section. This is
not certification because it was devised after the hidden key was opened.

It shows that these 93 cases mostly belong on the deterministic code path, not
the Qwen path. A fresh test for Qwen should contain only cases left genuinely
ambiguous after that code screen.

## Run facts

- Model: `qwen3.6:35b-a3b`, GGUF Q4_K_M
- Calls: 93 separate sequential calls
- Runtime: 1,510.339 seconds (25m 10.339s)
- Prompt tokens: 451,056
- Output tokens: 712
- Transport failures: 0
- Completed-answer retries: 0

One finalization check briefly observed a different volatile `resident` status.
The model name, digest, size, quantization, and Ollama version were unchanged.
Finalization resumed without making a model call.

## Frozen hashes

- Manifest: `71fdd0e315cd7def57462a8c0c19f37fb8ab520bdf8a5d87a347f067d3fc2c01`
- Cases: `4c1a9083e56c467e3f3997b4c77f770ce34dd2b3631332bb16b07b88b3fe88a3`
- Raw results: `5e7aa70599784e650314fdf58703d0c464937c2009b5bde4f14c7cebc729f2af`
- Score: `7ac18f5064d60213b064a6ab84ab24acd2b38b87ef8f03a60c65938c330546a8`
