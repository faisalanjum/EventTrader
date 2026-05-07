# Validation report — SEC ground truth + Rule G2 simulation

- Total manifest rows: **408**
- Tier A: 334
- Tier B: 66
- Tier C: 7
- Unclear: 1
- Tier A+B coverage: **400** / 408 = 98.0%

## Candidate D on Tier A+B rows
- fail_closed: 293
- true: 95
- false: 12

## Candidate D on all non-unclear rows (Tier A+B+C)
- fail_closed: 293
- true: 95
- excluded: 7
- false: 12

## G2-calendar-only on Tier A+B rows
- true: 316
- fail_closed: 35
- false: 49
- changed_vs_d (any tier): 263
- D fail-closes flipped to correct AUTO_OK on Tier A+B: **221**
- D fail-closes flipped to wrong AUTO_OK on Tier A+B: **37**
- New wrong AUTO_OK on Tier A+B: **37**

## G2-all-fy-disagreement on Tier A+B rows
- true: 334
- false: 51
- fail_closed: 15
- changed_vs_d (any tier): 283
- D fail-closes flipped to correct AUTO_OK on Tier A+B: **239**
- D fail-closes flipped to wrong AUTO_OK on Tier A+B: **39**
- New wrong AUTO_OK on Tier A+B: **39**

## PHR / PINC / PRU detail
### PHR  (14 rows)
- D outcome 'true': 12
- D outcome 'fail_closed': 1
- D outcome 'false': 1
- G2-calendar-only changes: total 0, correct 0, wrong 0
- G2-all changes: total 0, correct 0, wrong 0

### PINC  (10 rows)
- D outcome 'true': 6
- D outcome 'false': 3
- D outcome 'fail_closed': 1
- G2-calendar-only changes: total 0, correct 0, wrong 0
- G2-all changes: total 0, correct 0, wrong 0

### PRU  (15 rows)
- D outcome 'true': 12
- D outcome 'excluded': 2
- D outcome 'fail_closed': 1
- G2-calendar-only changes: total 0, correct 0, wrong 0
- G2-all changes: total 0, correct 0, wrong 0

## Per-ticker breakdown

| Ticker | Rows | Tier A+B | D correct | D wrong | D fail-closed | G2-calendar fixes correct | G2-calendar fixes wrong | G2-all fixes correct | G2-all fixes wrong |
| ------ | ---- | -------- | --------- | ------- | ------------- | ------------------------- | ----------------------- | -------------------- | ------------------ |
| ACI | 13 | 13 | 0 | 0 | 13 | 6 | 0 | 13 | 0 |
| ANF | 9 | 9 | 0 | 0 | 9 | 7 | 2 | 7 | 2 |
| ASO | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| BJ | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| BOX | 13 | 13 | 6 | 0 | 7 | 0 | 6 | 0 | 6 |
| BURL | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| CHWY | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| CNM | 12 | 12 | 0 | 0 | 12 | 11 | 1 | 11 | 1 |
| DKS | 12 | 10 | 0 | 0 | 10 | 5 | 5 | 5 | 5 |
| DLTR | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| FIVE | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| GBX | 15 | 14 | 12 | 0 | 2 | 0 | 1 | 0 | 1 |
| GIII | 12 | 12 | 0 | 0 | 12 | 0 | 12 | 0 | 12 |
| GME | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| KR | 13 | 13 | 0 | 2 | 11 | 2 | 0 | 11 | 0 |
| KSS | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| LOW | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| LULU | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| NTAP | 13 | 13 | 10 | 0 | 3 | 0 | 0 | 0 | 2 |
| NTNX | 13 | 13 | 9 | 1 | 3 | 0 | 2 | 0 | 2 |
| OLLI | 12 | 12 | 0 | 2 | 10 | 10 | 0 | 10 | 0 |
| OXM | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| PHM | 14 | 14 | 12 | 0 | 2 | 0 | 0 | 0 | 0 |
| PHR | 14 | 14 | 12 | 1 | 1 | 0 | 0 | 0 | 0 |
| PINC | 10 | 10 | 6 | 3 | 1 | 0 | 0 | 0 | 0 |
| PLAY | 12 | 12 | 0 | 1 | 11 | 9 | 0 | 11 | 0 |
| PLCE | 8 | 7 | 0 | 0 | 7 | 7 | 0 | 7 | 0 |
| PRU | 15 | 13 | 12 | 0 | 1 | 0 | 0 | 0 | 0 |
| PVH | 12 | 10 | 0 | 0 | 10 | 9 | 1 | 9 | 1 |
| RH | 14 | 14 | 0 | 2 | 12 | 9 | 0 | 9 | 0 |
| ROST | 2 | 2 | 0 | 0 | 2 | 2 | 0 | 2 | 0 |
| ULTA | 12 | 12 | 0 | 0 | 12 | 12 | 0 | 12 | 0 |
| WDAY | 15 | 15 | 10 | 0 | 5 | 0 | 4 | 0 | 4 |
| WMS | 11 | 11 | 6 | 0 | 5 | 0 | 3 | 0 | 3 |

## Caveats and blockers

- Companion periodic discovery uses SEC issuer submissions feed; older accessions may not have a same-FY companion 10-Q/10-K (filings split across years).
- Companion XBRL FY/Q is parsed from the primary 10-Q/10-K HTML iXBRL DEI tags. Some older filings store these as separate XBRL files we do not fetch; in that case the row stays at Tier C.
- 'unclear' rows are typically 8-K/A amendment-style filings or earnings releases that buried the quarter token in comparative or guidance text only.
- All evidence quotes are verifiable against the cached `raw_sec/{accession}/{doc}` files.
