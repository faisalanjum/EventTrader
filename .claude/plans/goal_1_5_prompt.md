# Goal 1.5 — Stratified Audit Packets for Human Review

**Status**: ready to fire AFTER Goal 1's verifier exits 0.
**Purpose**: catch the residual ~0.2-0.5% errors that two-source agreement might share-blindspot on (concentrated in known calendar-edge buckets).
**Trusted gate**: human verdict on packets, NOT LLM judgment.
**Codex's role**: PREPARE packets mechanically — no quarter-determination judgment.
**Structural verifier**: `earnings-analysis/canary/quarter_resolver/verify_audit_packets.py` (hand-authored; Codex must NOT modify).

---

## Why this exists (briefly)

Goal 1 produces a corpus where ~99.5-99.8% of rows are correct. The residual ~10-25 errors out of ~5,000 are statistically concentrated in known-difficult buckets (52/53-week filers, retail FYEs, denylist-adjacent companies, etc.). A uniform random sample misses these. A stratified sample with explicit edge-case buckets catches them with high statistical power.

The packets are **deterministic to generate**: they pull SEC EDGAR URLs, EX-99.1 first 500 chars (human-readable, NOT regex-parsed), XBRL/math fields, and structural metadata. The packet itself contains zero judgment — it just lays out the evidence so a human can verify in <30 seconds per row.

---

## Pre-flight (you do this before firing)

```bash
cd /home/faisal/EventMarketDB
# Confirm Goal 1 verifier passes
venv/bin/python earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py
# Expect: ALL CHECKS PASSED — Goal 1 corpus verified

# Confirm Goal 1 outputs are in place
ls -la earnings-analysis/canary/quarter_resolver/{ground_truth.csv,needs_review.csv,build_corpus.py,REPORT.md}
```

Then commit them so subsequent /goal can't accidentally overwrite:

```bash
git add earnings-analysis/canary/quarter_resolver/{ground_truth.csv,needs_review.csv,build_corpus.py,REPORT.md,verify_audit_packets.py}
git commit -m "wip(quarter-resolver): Goal 1 corpus + audit-packet verifier"
```

---

## The /goal command (copy verbatim into Codex)

```
/goal Generate stratified SEC-linked audit packets from Goal 1's
ground_truth.csv to enable human verification of corpus correctness on
high-risk and representative rows. This is a MECHANICAL packet-generation
task — you do NOT determine quarter identity yourself; you assemble
evidence for the human reviewer. Read the running plan at
/home/faisal/EventMarketDB/.claude/plans/quarter-identity-resolver.md
FIRST.

CONTEXT
- Goal 1 corpus exists at earnings-analysis/canary/quarter_resolver/{ground_truth.csv, needs_review.csv}
- Verifier has passed (you can confirm by running it; it must still exit 0)
- DO NOT modify Goal 1's outputs, verify_ground_truth_corpus.py, or
  verify_audit_packets.py under any circumstance
- Existing helpers (read-only):
  - fye_month.get_fye_month
  - fiscal_math.period_to_fiscal (for verbose-form display only — not a judgment call)
  - get_quarterly_filings.XBRL_DENY_PERIODIC_ACCESSIONS

INPUTS AVAILABLE
- ground_truth.csv (the corpus)
- Neo4j: read-only access to Report, Company, Industry, Sector, ExhibitContent
- For each accession, you can fetch:
  - 8-K's stored exhibits (HAS_EXHIBIT → ExhibitContent) — pull EX-99.1 first
    500 chars from the .content field (this is human-readable text snippet only,
    NOT machine-parsed; the snippet is for the human reviewer's eyes)
  - Previous 8-K (chronologically prior earnings 8-K for same ticker)
  - Industry/sector classification
- SEC EDGAR URL pattern: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=8-K&dateb=&owner=include&count=40

OUTPUTS REQUIRED (under earnings-analysis/canary/quarter_resolver/)

1. audit_packets.json — array of packet objects, one per sampled row.
   Schema per packet:
     {
       "bucket": "<one of: random | week_52_53 | non_dec_fye |
                          q4_10k | denylist_adjacent | boundary>",
       "accession_8k": "0000831259-25-000048",
       "ticker": "FCX",
       "filed_8k": "2025-10-23T08:06:14-04:00",
       "filed_8k_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000831259&type=8-K&dateb=&owner=include&count=40",
       "accession_archive_url": "https://www.sec.gov/Archives/edgar/data/831259/000083125925000048/",
       # ↑ direct link to THIS filing's archive directory.
       # Pattern: https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/{accession_no_dashes}/
       # cik_no_leading_zeros = int(cik) (strips "00..." prefix)
       # accession_no_dashes  = accession_8k.replace("-", "")
       "ex_99_1_first_500_chars": "<verbatim excerpt from ExhibitContent.content for EX-99.1; truncate at 500 chars; preserve newlines>",
       "matched_periodic": {
         "accession": "0000831259-25-000054",
         "form_type": "10-Q",
         "period_of_report": "2025-09-30",
         "filed": "2025-11-04",
         "filed_after_8k": true
       },
       "xbrl": {
         "fy": 2025,
         "q": "Q3",
         "raw_fiscal_year_focus": "2025",
         "raw_fiscal_period_focus": "Q3"
       },
       "fiscal_math": {
         "fy": 2025,
         "q": "Q3",
         "fye_month": 12,
         "form_type_used": "10-Q"
       },
       "denylist_adjacent": false,
       "fye_class": "calendar_year",
       "prev_8k": {
         "accession": "0000831259-25-000033",
         "filed": "2025-07-23T08:09:14-04:00"
       },
       "human_verdict": null
     }
   The human will fill in human_verdict ∈ {"ok", "wrong", "unclear"}.

2. audit_packets.csv — flattened version of the JSON for spreadsheet review.
   One row per packet. Columns mirror the JSON structure with dotted notation
   (matched_periodic.accession, xbrl.fy, etc.).

3. SAMPLING_REPORT.md — concise (200-400 words):
   - Sample sizes per bucket
   - Distribution stats (sectors, FYE months, year ranges)
   - Any buckets that ran out of eligible rows (and why)

SAMPLE COMPOSITION (target 150-200 packets total, NO MORE)

Bucket   | Filter                                                      | Target
---------|-------------------------------------------------------------|-------
random   | uniform random across ground_truth.csv                       | 100
week_52_53 | rows where period_of_report.day in {28,29,30,31,1,2,3,4,5} AND fye_month != 12 (52/53-week filers + retailers with non-Dec FYE having day≤5 adjustments fire) | 20
non_dec_fye | rows where fye_month ∉ {12} (e.g., Aug=COST, Feb=URBN/HD/LOW) | 20
q4_10k   | rows where form_type_periodic == "10-K" (annual report; q_xbrl=FY mapped to Q4) | 20
denylist_adjacent | rows where ticker shares CIK with any accession in XBRL_DENY_PERIODIC_ACCESSIONS — i.e., the COMPANY had a known-bad XBRL filing on a sibling row, even if this specific row is fine | 20
boundary | rows with smallest 20 values of (matched.created - filed_8k) — closest to the structural cutoff | 20

De-dup across buckets: each accession appears in EXACTLY ONE bucket. Priority
order if a row qualifies for multiple buckets (first match wins):
  1. boundary
  2. denylist_adjacent
  3. q4_10k
  4. week_52_53
  5. non_dec_fye
  6. random

If an edge bucket has fewer than its target rows in the corpus, document the
shortfall in SAMPLING_REPORT.md and fill the remainder from the random pool.
The random bucket is the only bucket allowed to exceed its target count.

PACKET QUALITY RULES
- ex_99_1_first_500_chars MUST be the actual exhibit text from ExhibitContent.
  If the 8-K has multiple exhibits, prefer EX-99.1 specifically. If EX-99.1
  is missing, leave the field empty and note "no_ex_99_1" in the packet.
- DO NOT extract or interpret the quarter from the exhibit text. The text is
  for the HUMAN reviewer to read; you do not analyze it.
- xbrl/fiscal_math fields come straight from the corpus row (don't re-derive).
- matched_periodic.filed_after_8k is a boolean: True iff
  matched_periodic.filed > filed_8k.
- prev_8k = the chronologically prior earnings 8-K for this ticker
  (formType=8-K AND items CONTAINS '2.02', max created < this 8-K's created).
  If none exists (cold ticker first earnings), set prev_8k=null.

NON-GOALS
- Do NOT modify the verifier or Goal 1 outputs.
- Do NOT modify verify_audit_packets.py.
- Do NOT modify any production code.
- Do NOT make any quarter-identity judgments yourself.
- Do NOT fill in human_verdict — leave null.
- Do NOT exceed 200 packets total.
- Do NOT add more buckets than specified.
- Stay within earnings-analysis/canary/quarter_resolver/ and /tmp/.

DONE WHEN
The structural verifier exits 0:
  cd /home/faisal/EventMarketDB
  venv/bin/python earnings-analysis/canary/quarter_resolver/verify_audit_packets.py

The verifier checks:
  P1.  verify_audit_packets.py is git-clean (anti-tampering)
  P2.  audit_packets.json, audit_packets.csv, and SAMPLING_REPORT.md exist
  P3.  Total packet count is in [150, 200]
  P4.  Every packet has all required top-level and nested fields
  P5.  No duplicate accession_8k across packets
  P6.  Every packet's accession_8k exists in ground_truth.csv
  P7.  Every bucket is one of the allowed buckets
  P8.  Edge buckets do not exceed target counts; random may backfill shortfalls
  P9.  human_verdict is null on every packet
  P10. filed_8k_url and accession_archive_url are well-formed SEC URLs

WORKFLOW HINTS
- Read ground_truth.csv first; build the bucket assignments.
- Pull EX-99.1 snippets via Cypher in batches (avoid one query per packet).
- Sort packets by bucket then ticker before writing — deterministic order.
- After generation, do a self-check: every packet's accession_8k appears in
  ground_truth.csv exactly once, and bucket counts match the table.
- Run the structural verifier and iterate until it exits 0. Do not declare
  done until it passes.
```

---

## What we hand-wrote vs what Codex produces

| Artifact | Source |
|---|---|
| Sampling rules + bucket definitions | **Hand-written by us** (in this prompt) |
| Packet schema | **Hand-written by us** |
| `audit_packets.json` / `.csv` | Codex produces (mechanically — no judgment) |
| `SAMPLING_REPORT.md` | Codex produces |
| **Human verdict on packets** | **You** |

---

## What you do AFTER Codex finishes

1. Open `audit_packets.csv` in a spreadsheet OR open `audit_packets.json` in a viewer.
2. For each packet (~30 sec each):
   - Click `filed_8k_url` → SEC EDGAR page for the 8-K
   - Read `ex_99_1_first_500_chars` — the press release header should clearly state the quarter
   - Confirm: does the press release's stated quarter match `fiscal_math.q` and `fiscal_math.fy`?
   - Mark `human_verdict` = `ok` / `wrong` / `unclear`
3. Total time: ~150-200 packets × 30 sec = ~75-100 minutes.

## Pass criteria for Goal 1.5

- 0 `wrong` verdicts → corpus passes; proceed to Goal 2.
- 1+ `wrong` verdicts → corpus has a real defect; investigate root cause, fix `build_corpus.py` (or the structural filter, or DENY list), re-run Goal 1 + Goal 1.5.
- ≤2-3 `unclear` verdicts → acceptable; document in audit log.
- Many `unclear` → indicates packet schema doesn't give enough evidence; revise packet schema and re-run Goal 1.5.
