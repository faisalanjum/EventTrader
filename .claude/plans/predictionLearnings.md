# Prediction Learnings — CRM Q4 FY2025 Post-Mortem

## The Result
- **Hourly prediction: CORRECT** — predicted +4% to +7%, actual +3.71% adjusted
- **Daily prediction: WRONG** — predicted +5%, actual -4.01% (-2.40% adjusted)
- Root cause: -3.64% sector selloff overwhelmed positive earnings reaction

---

## Data Gaps That Cost Us

### 1. Consensus Section Was Empty (FIXED — buy AV $50/mo key)
- Alpha Vantage has 87 quarterly rows with beat/miss history + revision trends
- Free tier rate limit (25/day) caused the builder to get zero rows
- Fix: upgrade to Plan 75 ($49.99/mo, 75 req/min, no daily limit)
- No code changes needed — builder works correctly once data arrives

### 2. No Post-Filing Data Feed (ARCHITECTURAL GAP)
- Macro snapshot was frozen at filing time (4:03 PM Feb 26)
- By 8 AM Feb 27, sector futures showed -2%+ decline — invisible to the predictor
- This single pre-market check would have flipped -4% loss → +2-3% win

---

## Required Multi-Stage Architecture

| Stage | Trigger | Data Feed | Decision |
|-------|---------|-----------|----------|
| **1. Filing** | 8-K drops | Press release + macro snapshot + consensus | Initial direction + magnitude |
| **2. Transcript** | Call ends (~T+2hr) | Earnings call Q&A tone | Confirm/reduce conviction |
| **3. Pre-market** | T+16hr (~8 AM) | SPY/sector futures, VIX, analyst notes | **Hold / reduce / exit** |
| **4. Intraday** | Open + 30min | Gap fade pattern, sector trend | Trail stop or exit |

**Stage 3 is the highest-ROI addition.** One pre-market macro check prevents riding a fading gap into a loss.

---

## Trade Management Rules (Derived from CRM)

1. **Size for uncertainty** — hostile macro at filing time (tech -4.67% 5d) → start at 60% size, not 100%
2. **Pre-market sector check** — if XLK futures down -1%+ worse than filing snapshot, take profit before open
3. **Gap fade rule** — if earnings gap loses 50% in first 30 minutes, exit entirely
4. **Sector hedge option** — long CRM + short XLK isolates the earnings signal from macro noise (CRM adjusted hourly was +3.71% even on a -3.64% sector day)

---

## What the Data Bundle Does Well (Keep)

- 8-K + EX-99.1 press release: full results, guidance, management quotes
- Multi-quarter XBRL financials: margin trends, cash flow trajectories
- Inter-quarter events with forward returns: prior quarter reaction patterns
- Peer earnings reactions: how THIS market regime treats beats vs misses
- Macro snapshot at filing time: starting conditions

## What Consensus Adds (After AV Upgrade)

- Historical beat/miss calibration: "CRM typically beats by 3-8%, so 6.5% is strong but not exceptional"
- Beat streak tracking: Q3 miss broke a long streak, Q4 is return to form
- avg_eps_surprise_pct_last4: quantified baseline for surprise magnitude
- **In live mode only**: forward estimates with 7/30/60/90 day revision momentum

## Accuracy Ceilings by Window

| Window | Current Bundle | After AV Fix | After Multi-Stage | Theoretical Max |
|--------|---------------|-------------|-------------------|-----------------|
| Hourly (earnings reaction) | ~60% | ~63% | ~65% | ~72-75% |
| Session | ~57% | ~60% | ~63% | ~68-72% |
| Daily (close-to-close) | ~53% | ~55% | **~62%** | ~65% |

The daily jump from 55% → 62% comes almost entirely from Stage 3 (pre-market macro check), not from better earnings analysis.

---

## Action Items

- [ ] Buy AV Plan 75 ($49.99/mo) — [alphavantage.co/premium](https://www.alphavantage.co/premium/)
- [ ] Build Stage 3: pre-market macro updater (SPY/XLK futures + VIX at ~8 AM)
- [ ] Add transcript ingestion to pipeline (earnings call available ~T+2hr via SEC or vendor)
- [ ] Implement gap fade monitor (30-min post-open check)
- [ ] Consider sector hedge framework (long stock + short sector ETF)

---

## Bundle Rendering Format Review (CCL Q1 FY2026)

### Overall: Very good, not perfect. ~85/100 for LLM comprehension.

### What works well

1. **Numbered section structure** — The `## 2.` through `## 9.` hierarchy is immediately scannable. I can jump to any section by concept.

2. **Consistent table formatting** — Markdown tables throughout. The prior financials (Section 5) are especially clean: metric x quarter grids with consistent formatting.

3. **Metadata header** — The 3-line header (`Filed:`, `Mode:`, `PIT cutoff:`) is compact and tells me exactly the temporal frame of reference before anything else.

4. **Beat/miss summary line** — `4 EPS beats in last 4 quarters | Avg EPS surprise +29.2%` is a perfect one-line digest before the detail table.

5. **Inter-quarter events schema annotation** — `Schema: inter_quarter_context.v1` and the adjusted returns legend make the data self-documenting.

6. **Guidance tables with Current/Prior/Change** — The three-column design makes trajectory tracking intuitive.

---

### Issues that hurt comprehension

**1. Section 2: The EX-99.1 press release is a wall of unstructured text (~13 pages raw)**

This is the single biggest problem. Lines 15 is one continuous blob containing the income statement, balance sheet, statistical information, non-GAAP reconciliations, and legal boilerplate — all flattened into a single cell. The financial tables (CONSOLIDATED STATEMENTS OF INCOME, BALANCE SHEETS, etc.) lost all columnar structure when rendered as inline text. For example:

```
Passenger ticket $ 4,023 $ 3,832 Onboard and other 2,142 1,978 Total Revenues 6,165 5,810
```

This is *parseable* but not *readable*. I have to mentally reconstruct the columns. Compare this to how Section 5 presents the same data — clean markdown tables where every column is visually distinct.

**Recommendation**: Either:
- Pre-extract the key numbers into a structured table (like Section 5 already does for historical data), and relegate the raw press release to an appendix/reference, OR
- At minimum, re-render the embedded financial tables as markdown tables within this section

**2. Guidance section (3) has duplicate/near-duplicate entries**

Multiple rows for the same metric in the same period with slightly different wording:
- FY2024: `Capacity Growth ~4.7%` and `Capacity Growth ~4.8% YoY` (lines 66-67)
- FY2024: `Basic Share Count ~1.27B` appears twice (lines 63-64)
- FY2025: `Fuel Cost per Metric Ton` has 3 entries: `~$617M`, `~624`, `~$617` (lines 125-127)
- FY2024: `ROIC` has `"double digit"` and `~10.5%` separately (lines 97-98)

These look like different guidance vintages that weren't collapsed. For an LLM trying to determine "what is the current guidance?", this creates ambiguity.

**Recommendation**: Deduplicate to one canonical "latest" row per metric-period. Move superseded values to the History table.

**3. News events (Section 6) have many missing titles**

N1-N13, N29, N33, N35 all show `— | —` for Title and Channels. These correspond 1:1 with the 425 filings (F1-F13), so they're duplicate noise — the same event appears in both News and Filings tables with no added information.

**Recommendation**: Deduplicate news rows that are just filing echo events, or at minimum populate the title from the filing form type.

**4. Guidance History table (lines 367-422) overlaps heavily with the FY tables above**

The "Current/Prior/Change" tables already show the latest + one prior. The History table then re-lists many of the same data points with dates. This is useful for trajectory analysis but creates confusion about which is authoritative.

**Recommendation**: Make the relationship explicit. Either label the FY tables as "Latest Guidance Snapshot" and the History table as "Full Revision Timeline", or merge them.

**5. Units inconsistency in guidance**

- `ALBDs` is shown as `~$91.3M` (line 25) — the `$` is wrong, ALBDs aren't dollars
- `Fuel Cost per Metric Ton` alternates between `~$617M` (line 125, the M is wrong — it's dollars not millions) and `~624` (line 126, missing the $ sign)
- Some metrics use `~` prefix, others don't

**Recommendation**: Standardize units. Remove `$` from non-dollar metrics. Ensure `M`/`B` suffixes are correct.

**6. Macro section (8) is compact but the catalysts table could use impact annotations**

The macro catalysts list events but don't indicate relevance to CCL specifically. The Iran shipping prohibition (N49 equivalent) is obviously critical for a cruise line but nothing in the table distinguishes it from generic market events.

---

### Minor suggestions

- **Section numbering starts at 2** — Section 1 is missing (presumably Company Profile / ticker metadata?). Mildly confusing.
- **Trading days table** has `Bnd` column that's mostly empty except `prev` and `cutoff` — could be removed or explained.
- **The `Trd` column** shows `N` for non-trading days that also lack price data — these rows add no information and could be omitted or compressed to a single "gap" annotation.

### Bottom line

The **structure is excellent** for LLM processing — numbered sections, markdown tables, metadata headers. The main pain points are: (a) the raw press release blob in Section 2 destroying what's otherwise a well-structured document, (b) duplicate/near-duplicate guidance rows, and (c) minor unit inconsistencies. Fix those three and this is close to ideal.
