# Goal 1 — Build the Quarter-Resolver Ground-Truth Corpus

**Status**: ready to fire via `/goal` after verifier is git-committed.
**Verifier**: `earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py` (hand-authored — Codex must NOT modify; will be checked via git diff).
**Pass criterion**: verifier exits 0.
**Honest claim**: this corpus is the strongest deterministic HISTORICAL ground-truth corpus + classified residuals. It does NOT cover live/no-periodic cases (those are Goal 2/3 territory and remain fail-closed until proven).

---

## Pre-flight (you do this BEFORE firing /goal)

```bash
cd /home/faisal/EventMarketDB
# Verifier must be committed so the git-diff freeze check has a baseline
git add earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py
git commit -m "wip(quarter-resolver): hand-written goal 1 verifier"
# Confirm clean
git diff --quiet -- earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py && echo OK
```

If the commit step is skipped, the verifier will fail at C1 with exit code 2.

---

## The /goal command (copy this verbatim into Codex)

```
/goal Build the high-confidence two-source-agreement ground-truth corpus
for the quarter-identity resolver investigation. Read the running plan at
/home/faisal/EventMarketDB/.claude/plans/quarter-identity-resolver.md FIRST,
in full, before doing anything else; that plan defines the problem,
ground-truth philosophy, and your scope. Your output must satisfy the
INDEPENDENT verifier at
earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py.
The verifier exits 0 when (and only when) the work is correctly done.
DO NOT MODIFY THE VERIFIER UNDER ANY CIRCUMSTANCE — it is git-committed and
the verifier will refuse to run if you have changed it.

CONTEXT (do NOT spend budget rediscovering — these are confirmed facts)
1. Bug location: scripts/earnings/quarter_identity.py:36, 200-265 — the
   constant _STALE_MATCH_DAYS=150 silently accepts the previous quarter's
   10-K as authoritative for live-mode 8-Ks (FCX Q1_FY2026 case).
2. Universe: earnings 8-Ks defined as
   formType="8-K" AND items CONTAINS "2.02" AND pf.daily_stock IS NOT NULL.
3. 8-K XBRL ingestion: ALL earnings 8-Ks have xbrl_status="SKIPPED" —
   universally absent in our graph by deliberate scope decision (NOT a
   subscription issue). Do NOT try to use 8-K XBRL.
4. 8-K cover-page XBRL doesn't reliably carry fiscal-period tags anyway
   (entity-ID metadata only). Do not chase this path.
5. period_to_fiscal in fiscal_math.py:13 is 99.1% validated against SEC's
   DocumentFiscalPeriodFocus on 549 filings (see docstring lines 14-40).
6. _map_event_to_quarter_end (filing→quarter direction) is unvalidated
   heuristic — do NOT use it for ground truth construction.
7. XBRL_DENY_PERIODIC_ACCESSIONS in get_quarterly_filings.py:307 lists
   ~11 known-bad periodic XBRL filings — your output MUST exclude these
   (they belong in needs_review.csv with reason="denylist").
8. should_use_xbrl_fiscal proximity guard (±1 year, ±1 quarter) — apply
   this filter; rows it rejects are needs_review with reason="proximity_rejected".
9. EX-99.1 text mining is OFF the table (per user constraint). Do not
   attempt regex parsing or LLM-based extraction of press release text.
10. STRUCTURAL CONSTRAINT (FCX-shape exclusion): for ground_truth.csv,
    the matched periodic must be the SAME-EVENT periodic, defined by
    matched.created > filed_8k (the periodic was filed AFTER the 8-K —
    same-quarter 10-Q/10-K is always filed after the same-quarter 8-K).
    Rows where matched.created <= filed_8k go to needs_review.csv with
    reason="not_same_event_periodic".

INPUTS AVAILABLE (re-use, do NOT reinvent)
- Neo4j driver pattern: see scripts/earnings/quarter_identity.py:165-180
- Production helpers (read-only imports):
  - fiscal_math.period_to_fiscal
  - get_quarterly_filings.parse_xbrl_fiscal_identity
  - get_quarterly_filings.should_use_xbrl_fiscal
  - get_quarterly_filings.XBRL_DENY_PERIODIC_ACCESSIONS
  - fye_month.get_fye_month
- Cypher pattern for matched periodic + structural same-event constraint:
  MATCH (q)-[:PRIMARY_FILER]->(c)
  WHERE q.formType IN ['10-Q','10-K']
        AND date(q.periodOfReport) < date(datetime(r.created))
        AND datetime(q.created) > datetime(r.created)   # ← SAME-EVENT
  ORDER BY q.periodOfReport DESC LIMIT 1
- Cypher for XBRL fiscal focus on matched periodic:
  see _QUERY in scripts/earnings/quarter_identity.py:40-87 for the pattern.

OUTPUTS REQUIRED (all paths under earnings-analysis/canary/quarter_resolver/)

1. ground_truth.csv — exactly these columns, in this order:
     accession_8k, ticker, filed_8k, period_of_report, fye_month,
     fy_xbrl, q_xbrl, fy_math, q_math, agreement,
     matched_accession_periodic, periodic_created, form_type_periodic
   Constraints:
     - agreement=True on every row (fy_xbrl == fy_math AND q_xbrl == q_math)
     - matched_accession_periodic is the RAW accession (NOT the PIT-masked
       one — i.e., the periodic's actual accession even when q.created >
       r.created). PIT-masking is for production resolver; this is ground
       truth construction.
     - matched_accession_periodic NOT in XBRL_DENY_PERIODIC_ACCESSIONS
     - periodic_created > filed_8k (structural same-event constraint)
     - should_use_xbrl_fiscal accepts (xbrl, fiscal_math) pair
   Minimum rows: 5,000.

2. needs_review.csv — same columns PLUS one extra column "reason".
   Schema:
     accession_8k, ticker, filed_8k, period_of_report, fye_month,
     fy_xbrl, q_xbrl, fy_math, q_math, agreement,
     matched_accession_periodic, periodic_created, form_type_periodic,
     reason
   Reason MUST be one of (priority order — first match wins):
     no_fye                  - fye_month not resolvable for this ticker
     not_same_event_periodic - no q with q.created > r.created exists
     no_xbrl                 - same-event periodic exists, lacks XBRL focus
     denylist                - matched_accession_periodic in DENY list
     proximity_rejected      - should_use_xbrl_fiscal returned False
     xbrl_math_disagree      - proximity OK but XBRL != fiscal_math

   Field population is canonical and verifier-enforced:
     - Always populate ticker, accession_8k, filed_8k.
     - Populate matched_accession_periodic, periodic_created,
       period_of_report, form_type_periodic when the same-event periodic exists;
       otherwise leave them blank.
     - Populate fye_month only when get_fye_month(ticker) resolves.
     - Populate fy_xbrl/q_xbrl only when XBRL fiscal focus parses.
     - Populate fy_math/q_math only when fiscal_math can be computed from
       fye_month + period_of_report + form_type_periodic.
     - agreement = "true" or "false" only when BOTH XBRL and fiscal_math exist;
       otherwise leave agreement blank.

3. build_corpus.py — the deterministic Python script that produced
   (1) and (2). Must be re-runnable and produce row-identical CSVs
   (sort GT and NR rows by (ticker, filed_8k, accession_8k) before write).

4. REPORT.md — concise (300-600 words):
   - Eligible universe size (= total rows in GT + NR)
   - GT row count + NR row count breakdown by reason
   - Sector/ticker distribution highlights
   - Any unusual findings (e.g., tickers with abnormally many NR rows)
   - Note that GT covers HISTORICAL cases only; NR's
     not_same_event_periodic bucket = live-mode rows handled by
     Goal 2/3.

UNIVERSE COVERAGE INVARIANT (verifier enforces — do NOT silently drop)
The eligible universe is ALL earnings 8-Ks (the formType + items + daily_stock
filter above). Every accession in the universe MUST land in EXACTLY ONE of
{ground_truth.csv, needs_review.csv}. No overlap, no missing.

NO DUPLICATES INSIDE EITHER FILE: each accession_8k appears AT MOST ONCE
inside ground_truth.csv and AT MOST ONCE inside needs_review.csv. Combined
with the universe-coverage rule, this means each accession appears EXACTLY
ONCE across both files.

The verifier independently computes the universe via Cypher and asserts:
  - union(GT.accession_8k, NR.accession_8k) == eligible_universe
  - intersection(GT, NR) is empty
  - no duplicates inside either file
  - FULL re-derivation: every eligible row independently classified by the
    verifier (NOT a sample) — every GT/NR row's fiscal labels, structural
    values, and copied metadata fields must match, and every NR row's reason
    must match the canonical reason
If you skip hard cases (cherry-pick easy ones) or duplicate any row, the
verifier will fail.

PRIORITY ORDER FOR REASON CODE ASSIGNMENT
For each universe row, determine its category by trying these in order;
first match wins:
  1. no_fye                  → if get_fye_month(ticker) returns None
  2. not_same_event_periodic → if no q satisfies (q.formType IN ['10-Q','10-K']
                                AND date(q.periodOfReport) < date(filed_8k)
                                AND datetime(q.created) > datetime(filed_8k))
  3. no_xbrl                 → matched periodic has no DocumentFiscalYearFocus
                                or DocumentFiscalPeriodFocus tags
  4. denylist                → matched_accession_periodic in DENY list
  5. proximity_rejected      → should_use_xbrl_fiscal returns False
  6. xbrl_math_disagree      → proximity OK but xbrl != fiscal_math
  Else → ground_truth (passes all checks)

NON-GOALS (do not do these)
- Do NOT modify the verifier file — it will fail the git-clean check.
- Do NOT modify any production code (scripts/earnings/*.py,
  .claude/skills/earnings-orchestrator/scripts/*.py, etc.).
- Do NOT touch earnings-analysis/Companies/, earnings-analysis/learnings/,
  earnings-analysis/.pre-v3-cutover-backup/.
- Do NOT use sec-api.io or any paid 3rd-party API.
- Do NOT attempt EX-99.1 text mining (regex or LLM).
- Do NOT propose fixes to the resolver — that is Goal 3.
- Stay within earnings-analysis/canary/quarter_resolver/ and /tmp/ for
  any scratch artifacts.

DONE WHEN (the verifier decides — not you)
The independent verifier exits 0:
  cd /home/faisal/EventMarketDB
  venv/bin/python earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py

The verifier checks (in order; first failure exits 1, infra issues exit 2):
  C1.  Verifier file is git-clean (catches tampering)
  C2.  All required deliverables exist + non-empty (ground_truth.csv,
       needs_review.csv, build_corpus.py, REPORT.md)
  C3.  GT schema EXACTLY matches REQUIRED_COLUMNS_GT (no extras, no missing)
  C4.  NR schema EXACTLY matches REQUIRED_COLUMNS_NR (no extras, no missing)
  C5.  No duplicate accession_8k inside GT or NR
  C6.  GT per-row invariants (agreement, valid quarter/year, raw-accession
       DENY check, structural same-event, date order, ticker, fye_month)
  C7.  NR per-row invariants (reason in VALID_REASONS, ticker valid)
  C8.  Universe coverage: union(GT,NR) == eligible_universe, no overlap,
       no missing — full corpus, not sample
  C9.  FULL re-derivation: ONE bulk Cypher returns every eligible row's
       context; verifier independently classifies EVERY row and asserts:
         - rows whose canonical classification is "ground_truth" are in GT
           with matching ticker, filed_8k, period_of_report, fye_month,
           xbrl/math labels, matched periodic accession, periodic_created,
           form type, agreement, and structural values
         - rows whose canonical classification is a reason code are in NR
           with that exact reason and matching copied metadata fields
       Catches every Codex error, not just statistical sample.
  C10. GT row count >= 5,000

If ANY of these fails, fix the issue and re-run. Do not declare done until
the verifier exits 0 in a clean run.

WORKFLOW HINTS
- Read the running plan AND the verifier script in full FIRST.
- Test on a single ticker (e.g., FCX) before running on full universe.
- Build deterministically: sort rows before writing CSVs.
- Run the verifier after each major change. Iterate until exit 0.
```

---

## What we hand-wrote vs what Codex produces

| Artifact | Source |
|---|---|
| `verify_ground_truth_corpus.py` | **Hand-written, git-committed BEFORE /goal** — Codex must NOT modify; verified via `git diff --quiet` |
| Pass criteria | **Hand-written by us** (in this prompt + the verifier) |
| `build_corpus.py` | Codex produces |
| `ground_truth.csv` | Codex produces |
| `needs_review.csv` | Codex produces |
| `REPORT.md` | Codex produces |

The verifier never trusts the agent's claims; it re-derives from raw Neo4j and re-classifies EVERY row independently (no sampling, full corpus).

---

## What to do AFTER /goal completes

1. Read REPORT.md for findings.
2. Run the verifier yourself (it should already pass per the agent — but you confirm independently):
   ```bash
   cd /home/faisal/EventMarketDB
   venv/bin/python earnings-analysis/canary/quarter_resolver/verify_ground_truth_corpus.py
   ```
3. If verifier passes, mark Goal 1 complete in the running plan's status tracker.
4. Move to Goal 1.5 (stratified audit-packet generation) — the agent prepares ~150-200 packets across 6 buckets; you (human) review them.
5. After Goal 1.5 audit clears, draft Goal 2 prompt (shadow-validator + algorithm proposals).
