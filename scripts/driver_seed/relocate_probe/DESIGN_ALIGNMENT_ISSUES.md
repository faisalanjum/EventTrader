# Relocation engine × FinalDesign — alignment verdict + recorded issues (2026-07-13)

Read via 3 parallel Opus readers over the FULL FinalDesign set (latest layer confirmed: 12 v1.3
ADJUDICATED w/ 2026-07-11 edits; amendment source = 66 §0.R; no doc says 11/12/14 superseded).
USER ORDER: record issues only — NO design or engine changes from this audit.

## VERDICT
The engine is the RIGHT generalizable substrate, in the RIGHT place: it is the raw-evidence feeder
UPSTREAM of the ITEM CONTRACT (12 FACT-17b). The design's part-2 producer (unwritten, 14 §2/§7) is
the layer that converts our evidence into DriverUpdate items. Philosophy aligns on every hard rule:
verbatim quote REQUIRED (DU-04) = our core guarantee · abstain-over-guess = the one-law fail-closed ·
store-as-stated (no computed numbers, DU-16) = our stated-only reads · YTD column discipline ≈
period_scope=ytd · deterministic XBRL lane feeds concept/member enrichment (steps 7/9, T12.9) ·
multi-axis full-member matching ≈ FS-09 never-drop. The 894-source historical backfill (90 §D) is
exactly this engine's fetch surface.

## ISSUES RECORDED (to bring up at the end)

### A. IDENTITY-DANGEROUS (over-merge = permanent under the one law)
1. 🔴 GAAP-vs-adjusted twin residual (~2%) is not just a precision miss — measurement is part of
   fact_scope → part of the FACT ID. A wrong twin = wrong id = silent over-merge. Design demands
   producer `measurement_raw_spans` (OD-9); our #768 fix (measurement flavor in address) is the same
   direction. PRIORITY RAISED: #768 should land before any production DriverUpdate feeding.
2. 🔴 Slice decomposition gap: engine emits raw XBRL members; design needs `kind:value` tokens,
   total→OMIT (never "total"), multi-part never-drop w/ code-sort (FS-09/15, FACT-26f), member links
   carrying slice_part anchors (FACT-28). Expected boundary — but the decomposition producer is
   UNWRITTEN (part 2); no engine change, just: it must exist before writes.
3. 🔴 metric-vs-surprise routing (ISS-16 §10.5): producer must DETECT stated actual-vs-expectation
   comparisons and emit metric + <metric>_surprise facts. Engine evidence must carry the FULL phrase
   → our quote windows must be wide enough to include the expectation clause (see B7).

### B. EVIDENCE-RECORD FIELD GAPS (additive enrichment of our output record; no redesign)
1. Value SHAPE: single scalar can't express range / floor / ceiling / numberless
   (level_low/high, "up to", "at least", value_text). Metric lane unaffected; GUIDANCE-lane fetches
   need shape-aware capture (note: live guidance extraction pipeline already covers guidance — the
   boundary may be intentional; confirm with owner).
2. Unit direction: design wants `unit_raw` VERBATIM + per-slot kind/money-mode hints
   (T8.3/8.4, FACT-23); we emit a normalized dimension (currency/percent/count) — right info,
   wrong direction. Must pass the raw wording through.
3. Period typing: need `time_type` (instant vs duration; start==end duration ILLEGAL → instant,
   ISS-23), `period_scope` (ytd/ttm/…+ sentinels), `sentinel_class` for dateless horizons, and exact
   start/end dates. Our period+period_evidence covers the window; the typing fields must be added.
4. Source envelope: `source_type ∈ {8k,transcript,10q,10k,news}` + `source_id` (Event anchor) +
   full-ISO PUBLIC timestamp — downstream collapse ranking depends on all three (09 §6.9, OD-14).
   Our bare `source` string is too thin.
5. XBRL evidence must carry (axis_qname, member_qname) PAIRS — member alone is meaningless (FS-21).
   xbrl_lane matches member sets; the emitted record should keep the pairs.
6. `grade` (exact|rounded|approx) has NO stored home in the 24-field record (derivation retired,
   09 §5). Keep engine-internal (QA/audit); it must denote SOURCE-stated approximation only, never
   our own rounding (DU-16 r3). Never feed it into supersession (09 §9 rank+time only).
7. Quote-span completeness: conditions, secondary baselines, unit wording and qualitative color live
   ONLY in the quote (final render fallback, 09 §6.4). Our number-window quotes may clip them —
   widen spans for producer-facing evidence (M14).
8. Level-vs-change separation ("rose 60 bps to 17.6%") + two units (level % / change bps, DU-17):
   engine emits one number per record; producer splits — evidence must group multiple records per
   sentence/event (fusion locality, T11.3): keep the source-event anchor on every record.
9. Sign: KEEP printing-faithful (parens preserved, never pre-signed) — downstream OD-12 does the
   signed-value-space conversion. Our SIGN-PRES stance is correct; do not "fix" signs in the engine.
10. PIT discipline (ISS-7): backfilling older periods must not use ADDRESSES built from later
    filings if the write is PIT-cut to event time — decide lock-recency vs PIT rules before the
    894-source backfill.
11. driver_name_raw must resolve to a catalog Driver WITH fact_type or be parked (DU-12) —
    admission/resolution layer is separate and part-2-blocked (expected; recorded for completeness).

### C. CONFIRMED NON-ISSUES
- Verdict fields (stock_impact/weightage/confidence) = producer judgment, correctly out of engine scope.
- driver_state = producer lane + prior-period memory, not evidence.
- Our multi-value single-`value` records: the CLI fuses within-event (FACT-17) — evidence stays granular.
- Adjusted-vs-GAAP as SAME driver, different measurement (E7/FS-25) matches our twin-fix direction.
