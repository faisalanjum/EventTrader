# QF-01 row-v3 development result

## Result

| Outcome | Count |
|---|---:|
| Correct | 93 |
| Wrong | 0 |
| Abstained | 0 |
| Invalid | 0 |
| Total | 93 |

Precision = **100%**. Recall = **100%**.

The test made 93 separate row-only calls. Qwen chose one source row or `null`;
deterministic code applied the request's stated left-to-right occurrence and
copied the exact source evidence. There were no retries, transport failures,
truncated responses, or model changes.

The formerly wrong cases now selected the correct `Gas Revenues` rows and the
correct `Third-party alumina shipments (kmt)` row.

## Boundary

This is a perfect result on an opened development set, not unseen
certification. It does not authorize production. Fresh positive, ambiguous,
and no-answer tables remain required.

## Run facts

- Runtime: 149.702 seconds
- Prompt tokens: 87,606
- Output tokens: 658
- Manifest: `6127437f486d57f52aec6e10f1a983799b1e81d0aaa8dd74328aa68cf31524f6`
- Raw results: `8be8187ee4a94f11154bfebbf3383238890d0ec956b8a0cb2b657fb895896477`
- Score: `1cdcce5b841f2bba91dc832987725c827f14094c0e24922262cea4909a239b82`
