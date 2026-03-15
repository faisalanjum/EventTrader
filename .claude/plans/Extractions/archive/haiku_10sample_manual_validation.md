# Haiku 10-Sample Manual Validation

Date: 2026-03-14

## Scope

Random sample of `10` non-earnings 8-K filings drawn from the hybrid Haiku bucket, meaning:

- excluded deterministic earnings (`2.02`)
- excluded deterministic anchor buckets such as clear `2.01` M&A, clear `1.01+2.03` debt, and clean `5.07` governance
- included filings where the hybrid design would actually ask Haiku to classify the event

Model used:

- `claude-haiku-4-5-20251001`

Output schema used:

- `primary_event`
- `secondary_events`
- `confidence`

Extended tag set used when meaningful:

- `EARNINGS`
- `GUIDANCE`
- `BUYBACK`
- `DIVIDEND`
- `RESTRUCTURING`
- `M_AND_A`
- `DEBT`
- `EXECUTIVE_CHANGE`
- `GOVERNANCE`
- `LITIGATION`
- `INVESTOR_PRESENTATION`
- `OTHER`
- `CYBER_INCIDENT`
- `RESTATEMENT`
- `ACCOUNTANT_CHANGE`
- `DELISTING_RIGHTS_CHANGE`
- `IMPAIRMENT`
- `SECURITIES_OFFERING`
- `PRODUCT_PIPELINE`
- `REGULATORY`
- `STRATEGIC_UPDATE`
- `CRISIS_COMMUNICATION`

Raw run artifact:

- `haiku_10sample_validation.json`

## Exact Sample Metrics

These are exact numbers for this manually reviewed sample of 10 filings.

### Primary label

- exact primary-label accuracy: `10/10 = 100.00%`

### Full label-set match

- exact filing-level set match: `9/10 = 90.00%`

### Multi-label micro metrics

- true positives: `11`
- false positives: `1`
- false negatives: `0`
- exact precision: `11 / 12 = 91.67%`
- exact recall: `11 / 11 = 100.00%`
- exact F1: `95.65%`

The single mistake was a secondary-label overcall:

- `WHD` (`0001104659-23-003802`) was correctly tagged `SECURITIES_OFFERING`, but Haiku also added `M_AND_A`, which was not supported by the filing text.

## Manual Review Table

| # | Ticker | Accession | Haiku primary | Haiku secondary | Confidence | Manual truth | Verdict |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| 1 | MPC | `0001510295-23-000057` | `EXECUTIVE_CHANGE` | `[]` | `0.95` | `EXECUTIVE_CHANGE` | Correct |
| 2 | LECO | `0001193125-23-190919` | `GOVERNANCE` | `[]` | `0.95` | `GOVERNANCE` | Correct |
| 3 | CDNA | `0001217234-23-000051` | `CRISIS_COMMUNICATION` | `[]` | `0.85` | `CRISIS_COMMUNICATION` | Correct |
| 4 | CVS | `0001193125-24-279907` | `DEBT` | `[]` | `0.95` | `DEBT` | Correct |
| 5 | NBIX | `0000914475-24-000229` | `PRODUCT_PIPELINE` | `[]` | `0.95` | `PRODUCT_PIPELINE` | Correct |
| 6 | MAA | `0000950170-25-007225` | `GOVERNANCE` | `[]` | `0.85` | `GOVERNANCE` | Correct |
| 7 | WHD | `0001104659-23-003802` | `SECURITIES_OFFERING` | `[M_AND_A]` | `0.95` | `SECURITIES_OFFERING` | Primary correct, secondary overcall |
| 8 | HOOD | `0001783879-24-000138` | `REGULATORY` | `[LITIGATION]` | `0.95` | `REGULATORY` + `LITIGATION` | Correct |
| 9 | PRU | `0001193125-24-033753` | `CYBER_INCIDENT` | `[]` | `0.99` | `CYBER_INCIDENT` | Correct |
| 10 | OKE | `0001628280-23-012601` | `DIVIDEND` | `[]` | `0.95` | `DIVIDEND` | Correct |

## Manual Verification Notes

### Clear wins

- `MPC`: director resignation -> `EXECUTIVE_CHANGE`
- `LECO`: board expansion / election of a director -> `GOVERNANCE`
- `CDNA`: explicit Silicon Valley Bank exposure denial -> `CRISIS_COMMUNICATION`
- `CVS`: tender offer for outstanding notes -> `DEBT`
- `NBIX`: commercial launch / FDA-adjacent product availability -> `PRODUCT_PIPELINE`
- `MAA`: death of long-term director -> `GOVERNANCE`
- `HOOD`: SEC Wells Notice -> `REGULATORY` + `LITIGATION`
- `PRU`: Item `1.05` cyber incident -> `CYBER_INCIDENT`
- `OKE`: explicit quarterly cash dividend declaration -> `DIVIDEND`

### Single error

- `WHD`: follow-on equity offering via underwriting agreement and pricing press release -> `SECURITIES_OFFERING` was right, but `M_AND_A` was unsupported

## Conclusion

For this random 10-filing sample from the hybrid Haiku bucket:

- primary-event classification was perfect: `100.00%`
- multi-label recall was perfect: `100.00%`
- the only observed error was one extra secondary tag, producing `91.67%` multi-label precision

This does **not** prove global production precision/recall.

What it does prove:

- on a small random sample of the actual non-earnings hybrid-Haiku bucket, Haiku performed very strongly
- the error mode in this sample was over-tagging a secondary label, not missing the main event
- this is consistent with the broader conclusion that Haiku is most useful on ambiguous non-earnings filings, while deterministic routing should still own obvious structural buckets
