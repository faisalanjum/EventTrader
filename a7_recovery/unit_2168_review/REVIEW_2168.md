# Immediate cause of every recall miss in the completed native score

Core, 2026-09-15. Read-only: no model call, no scorer run, no boundary job,
no replay needed - every fact below comes from saved artifacts.

## Two corrections I owe first

1. **The full key WAS supplied and I said it was not.** A7_CORRECTED_SCORE.json
   carries `key` with 33 sources and every gold field, Starlink included. Its
   Starlink gold row has `level_low: null`, so the key's row for that sentence
   is numberless while the record asserts 300. My 2167 disposition (d) said this
   "needs key-side evidence I was not given" - it was in the file I already had.
   The two rows are answerable; the semantic call is yours.
2. **I accept that my 86 are leads, not verified reader answers.** An equal
   sentence plus an equal numeric set does not establish the same population,
   time, units, bound or kind of fact, and some of those records have proved
   source errors. I do not restate them as correct here.

## Reconciliation to your trace — exact

CORRECTED_SCORE_TRACE_2167.json measures b3a759b5abf9fc94ab0c89f9e4826b7588f32cab7c25e02f516d9d6230942f27,
your published pin. It holds 448 rows, of which **185 recall_miss**: P1 42,
P2 49, UNION 94, over **105 unique (source, gold) positions** - all four numbers
reproduce exactly. Every one of the 185 is traced below; none is dropped.

Lane evidence: 192 G1 lanes map to a selected attempt with raw path and hash -
**162 from the original run** (unit_2088_real_grading/g1, root 013401e8…, the
pin in KEY_GRADING_INPUTS.original_g1) and **30 from the current reuse run**
(unit_2152_g1_reuse/g1). All 185 rows carry BOTH lanes' raw paths and hashes;
43 rows cite the reuse run on a lane.

**Your settled accounting reproduces independently.** 191 of 192 selected raw
answers parse after the owner's own fenced-block format recovery; the single
failure is **G1-050/G1a**, the exhausted lane. It is also the only lane the
finalizations mark invalid. I did not retry it.

## The 185, by immediate cause

| immediate cause | P1 | P2 | UNION | total |
|---|---|---|---|---|
| both readings agreed NO candidate | 39 | 42 | 34 | **115** |
| group withheld (multi-candidate or contended) | 3 | 1 | 58 | **62** |
| exhausted invalid lane | 0 | 5 | 0 | **5** |
| paired disagreement | 0 | 1 | 1 | **2** |
| selected, then not credited | 0 | 0 | 1 | **1** |
| TOTAL | 42 | 49 | 94 | **185** |

- **115 agreed no-candidate.** Both blind readings returned an EMPTY
  produced_idxs for that gold question - verified true for all 115. Neither
  reader found any produced record for the gold row. This is a producer recall
  miss on the evidence, not a test or matching fault.
- **62 group withheld.** 58 have both lanes agreeing on a MULTI-row selection
  (57 picked 2 rows, 1 picked 3), which cannot form a bijective pair; 4 more are
  contended, where another gold row in the same leg/source agreed on the same
  produced index. 59 unique positions. Both groups you already located fall out
  of this set without being rediscovered: **P1 0001104659-25-102611 gold 3, both
  lanes [3,4]** (the 329.5m and 6.7% renderings) and **P2 0000027904-26-000022
  gold 1, both lanes [1,2]** (1.2b and 9.4%).
- **5 exhausted invalid lane.** These are exactly the 5 rows your trace marks
  `ruling_present: false` - P2, source 0001104659-25-118458, gold 0 to 4 - and
  all five bind to batch **G1-050**, whose G1a lane is the one exhausted lane.
  No resolution entry exists for them because no valid pair was ever produced.
- **2 paired disagreement.** The two readings selected differently.
- **1 selected, then not credited.** UNION ULTA_2026-03-12T16.30 gold 5,
  question Qa46ca6933d9623c2: both lanes agreed on the single row [4], so the
  miss arises AFTER selection. That leg/source carries field-mismatch route
  codes (change_unit, comparison_baseline, level_shape_hint, level_unit,
  measurement-OD-9, value:change_value), but the saved counter events are keyed
  by leg/source and NOT by gold index, so I cannot bind a specific code to this
  row and I do not claim one. It belongs to your field-mismatch review.

## What this explains about the score

P1 and P2 recall misses are overwhelmingly agreed no-candidate (39 of 42, 42 of
49): the facts were not emitted. UNION is different - only 34 of 94 are
no-candidate while **58 of 94 are group withholding**. So the UNION recall gap
(43.0% against 74.6% and 70.3%) is driven mainly by the bijection gate, not by
missing facts.

That is the same gate reported from the other side in 2167: when one gold row
draws two agreed produced rows, the gold row becomes a recall miss AND both
produced rows become unmatched extras. One mechanism, two symptoms, in the same
events. I state this as the measured connection only; whether each pair really
is one claim is the identity/semantic question that remains yours.

## Limits

No route or namespace rejection is asserted for any row: the saved counter
events are per leg/source, not per gold, so I report them as context only. The
two paired-disagreement and one post-selection row are named individually rather
than grouped. No verdict, Boolean, match, key row or score was edited, and no
match was inferred from quotes or numbers - every selection above is the raw
produced_idxs the reader actually returned.

## Evidence in this unit

- `recall_miss_trace_185.json` - all 185 rows: leg, source, gold index, current
  question id, batch, both lanes with run/attempt/raw path/raw hash, both raw
  selections, the gold's candidate list, the native ruling and its presence,
  route codes at that leg/source, and the reasons.
- `g1_lane_evidence.json` - all 192 lanes to selected attempt, validity, raw
  path and raw hash.
- `REVIEW_2168.md` - this report.
