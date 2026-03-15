# Haiku 10-Sample Manual Validation Rerun

Date: 2026-03-14
Model: `claude-haiku-4-5-20251001`
Input sample: fresh random 10-filing rerun from the hybrid Haiku bucket using `.claude/plans/Extractions/run_haiku_10sample_validation.py`
Raw predictions: [haiku_10sample_validation.json](/home/faisal/EventMarketDB/.claude/plans/Extractions/haiku_10sample_validation.json)

## Method

For each of the 10 sampled filings:
- Run Haiku on the filing packet built from the actual `items`, top sections, and top exhibits.
- Read the filing packet manually.
- Assign manual ground truth for:
  - `primary_event`
  - `secondary_events`
- Compare Haiku output against manual truth.

Metrics reported:
- Primary-label accuracy
- Filing-level exact set match
- Multi-label precision
- Multi-label recall
- Multi-label F1

## Exact Results

- Primary-label accuracy: `10/10 = 100.00%`
- Filing-level exact set match: `9/10 = 90.00%`
- Multi-label precision: `12/13 = 92.31%`
- Multi-label recall: `12/12 = 100.00%`
- Multi-label F1: `96.00%`

## Manual Audit

### 1. BJ `0001104659-23-100791`
- Items: `5.02`
- Haiku: primary `GOVERNANCE`, secondary `[]`
- Manual truth: primary `GOVERNANCE`, secondary `[]`
- Why: board committee appointments for previously appointed directors; this is board governance, not a management change.
- Verdict: correct

### 2. DOCN `0001582961-24-000058`
- Items: `5.02`
- Haiku: primary `EXECUTIVE_CHANGE`, secondary `[]`
- Manual truth: primary `EXECUTIVE_CHANGE`, secondary `[]`
- Why: Chief Revenue Officer stepped down and transitioned to advisory status.
- Verdict: correct

### 3. WERN `0000793074-23-000034`
- Items: `7.01`, `9.01`
- Haiku: primary `INVESTOR_PRESENTATION`, secondary `[]`
- Manual truth: primary `INVESTOR_PRESENTATION`, secondary `[]`
- Why: filing announces participation in investment conferences and webcast/fireside-chat materials.
- Verdict: correct

### 4. BAX `0001628280-23-023907`
- Items: `5.02`, `9.01`
- Haiku: primary `GOVERNANCE`, secondary `[]`
- Manual truth: primary `GOVERNANCE`, secondary `[]`
- Why: board appointment and committee assignment; governance event.
- Verdict: correct

### 5. BBIO `0001140361-23-034684`
- Items: `7.01`, `8.01`, `9.01`
- Haiku: primary `PRODUCT_PIPELINE`, secondary `['INVESTOR_PRESENTATION']`
- Manual truth: primary `PRODUCT_PIPELINE`, secondary `['INVESTOR_PRESENTATION']`
- Why: positive Phase 3 trial data is the core event; investor slide deck is also attached.
- Verdict: correct

### 6. IOVA `0001104659-25-065781`
- Items: `5.02`
- Haiku: primary `EXECUTIVE_CHANGE`, secondary `[]`
- Manual truth: primary `EXECUTIVE_CHANGE`, secondary `[]`
- Why: CFO departure and interim finance officer appointment.
- Verdict: correct

### 7. APH `0001104659-25-057954`
- Items: `1.01`, `8.01`, `9.01`
- Haiku: primary `DEBT`, secondary `[]`
- Manual truth: primary `DEBT`, secondary `[]`
- Why: pricing and sale of senior notes; debt financing event.
- Verdict: correct

### 8. MSTR `0001193125-24-272923`
- Items: `7.01`, `8.01`
- Haiku: primary `SECURITIES_OFFERING`, secondary `['STRATEGIC_UPDATE']`
- Manual truth: primary `SECURITIES_OFFERING`, secondary `['STRATEGIC_UPDATE']`
- Why: the filing discloses ATM share issuance plus a substantive bitcoin holdings / BTC-yield strategy update.
- Verdict: correct

### 9. APA `0001193125-24-160708`
- Items: `9.01` only
- Haiku: primary `M_AND_A`, secondary `[]`
- Manual truth: primary `M_AND_A`, secondary `[]`
- Why: amendment filing with acquired-business financials and merger pro formas for the Callon transaction.
- Verdict: correct

### 10. X `0001163302-24-000011`
- Items: `7.01`, `9.01`
- Haiku: primary `EARNINGS`, secondary `['M_AND_A']`
- Manual truth: primary `EARNINGS`, secondary `[]`
- Why: the filing is a transcript covering fourth-quarter and full-year 2023 results; the Nippon merger is discussed only as background and not announced as a new event in this filing.
- Verdict: primary correct, secondary false positive

## Conclusion

On this fresh 10-filing manual audit:
- Haiku got every primary label right.
- The only observed error was one extra secondary label on `X`.
- The error mode is the same one seen earlier: secondary over-calling is the main residual risk, not missing the main event.
