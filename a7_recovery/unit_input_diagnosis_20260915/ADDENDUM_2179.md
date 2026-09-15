# Addendum — corrections after Codex SEQ 2179 review

ANALYSIS.md bytes are unchanged (sha256 `06c85ac40de6d2ed…`), as instructed.
This file records what his review corrected. Three qualifications; I accept all three.

---

## A. The 96.91% geometry claim — his code objection is CORRECT; the number survives

He wrote: *"96.91% geometry counts any covering header, not unique placement."*

He is right about the code. `scripts/geom_ambiguity.py:40` reads

```python
elif len({h[2] for h in cover})>=1: forced+=1
```

`len(...)>=1` is true for every non-empty `cover`, so the branch counted "at least one
header covers this position", not "exactly one". That test was written wrong.

**But the claim was about placement, and placement needs a per-header-ROW test, not a
distinct-label test.** A figure is legitimately covered by two header *levels*
("Three Months Ended" and "November 1, 2025"); levels stack, they do not compete.
Counting distinct labels across all header rows treats stacking as ambiguity and gives
41.17% — also wrong, in the other direction (`scripts/geom_ambiguity_v2.py`,
`results/GEOMETRY_V2.txt`, kept as the failed intermediate).

The correct test — on every header row, at most one cell of that row covers the column
position — is `scripts/geom_ambiguity_v3.py` -> `results/GEOMETRY_V3.txt`:

```
figures placed                                : 43037
  placement FORCED (<=1 cell per header row)  : 41709  (96.91%)
  no header covers it at any level            :  1328  ( 3.09%)
  AMBIGUOUS (a header row has 2+ covering)    :     0  ( 0.00%)
```

Same 96.91%, now measured by a test that can fail. The stronger result is the third
line: **zero ambiguous placements in 43,037 figures** — cells within one row cannot
overlap, so colspan geometry can never place a figure under two competing labels at the
same level. The original code reached the right number by accident; this one proves it.

## B. "The existing normalizer already restores the Health token" — ACCEPTED

ANALYSIS.md §5 says the repair means "Best Buy Health slice now found (the original P2
omission)". That is true of P2 and of these runs, but it must not be read as the repair
being what makes the token reachable: official P1 already contains it, and the
normalizer already restores it. The Health token is therefore **not** evidence for the
input-repair thesis. Withdrawn as support; the #048 column-assignment result is not
affected and stands on its own.

## C. "57/70 agreement is not a 19% score noise floor" — ACCEPTED

ANALYSIS.md §7 says "any intervention whose effect is smaller than ~19% grader noise
cannot be measured". That overstates. 0.8143 is a per record-aspect cell agreement rate
over 70 cells drawn from the 40 guidance questions, not a variance bound on the official
score. The defensible statement is narrower: **the grader gave different answers to the
same question on the same record, including one record ruled True, False and UNRESOLVED
across three askings** — so grader disagreement is demonstrated, and its effect on the
score is unquantified rather than bounded at 19%.

## D. "88.3% aggregate counters are not individually proved causes" — ACCEPTED

§6a labels whole error-code families **TRACED**. What was actually proved is that the
*rule* behind each family is absent from the served text (D1, D4, D5) or that the menu
and key disagree (D2, D3). Whether every one of the 88 period entries fails *for that
reason* was not checked entry by entry. The label should read "cause identified for the
family", not "cause proved for each entry". The 11.7% reader-judgment bucket remains
NOT EXAMINED, and no entry anywhere was examined and attributed to the reader.

---

## What still stands unqualified

- 85.2% of table row boundaries lost in the served text (15 filings, 15 filers).
- Two independent parsers agree 48 = 48 on the recovered grid.
- D1/D4/D5 rule absences and D2/D3 menu-vs-key splits, each checked against served bytes.
- `#048`: both runs identical, 27 of 31 fields correct, correct Q3-vs-YTD column
  assignment from a quote carrying no header.
- `#045`: two identical calls differed on `driver_name` and `period_end_date`.
