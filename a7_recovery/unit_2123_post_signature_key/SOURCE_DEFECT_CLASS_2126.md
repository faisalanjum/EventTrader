# SOURCE_DEFECT_CLASS_2126

The SAME 35 reported-metric facts, finished over the **complete** supplied
source parts, for Codex SEQ 2126 item 3, plus the procedural clarification item
item 3 asks for. Read-only: no call, no key or candidate edit, no grading, no
publication, no period work.

**Inputs**

| what | identity |
|---|---|
| full-part search (reading aid, judges nothing) | `core_full2126_c/FULL_PART_SEARCH_2126.json`, `4ccce0d1cc86f373902c361adbdc249fdb6d5f8ac41d48f5d2da7be596fd859b` |
| its enumerator | `inventory_full_part_2126.py` |
| final dispositions | `core_full2126_c/SOURCE_STATE_DISPOSITIONS_2126.json`, `b0f1c6ad0e1133f5cecb201a56c7fc23ec9ade73debda211817e57c9a7d98a91` |
| the 2125 evidence, preserved and superseded only on dispositions | `core_inv2125_a/SOURCE_DEFECT_INVENTORY_2125.json` `16fa94663269fdcab94b2c15de43cb236234328120c5de4d12d84cff93f18e26` |
| owning law | `FINAL_DESIGN.md` `4218d73abe6b98ef2ecd325aef8b5e49985101b122e457b39784dee677f32a0b` |

**How the window limitation was removed.** Every one of the 35 rows was re-read
against its whole part — 1,319,850 characters, 10,632 sentences in total. The
aid emits, per row, every sentence of the part sharing a word with that row's
own `raw_label_or_claim` or `driver_name` (4,696 sentences), and every line of
the part carrying that fact's own stored value (598 lines). Search terms come
from each row's own data; there is no direction vocabulary, no adjacency score
and no threshold that hides a sentence. Judgement is mine.

---

## 1. Result

| disposition | count |
|---|---|
| current state supported | **26** |
| needs independent source correction | **9** |
| genuinely unresolved | **0** |

Nothing is left unresolved. Evidence kinds behind the nine: **7 prior value**,
**2 stated direction**.

**The affected source set is seven:**
`0000027904-26-000020` · `0000092380-26-000044` · `0000898173-26-000006` ·
`0001041061-26-000003` · `0001104659-25-102611` · `0001104659-26-017090` ·
`BBY_2026-03-03T08.00`

### The nine, each with its actual supporting occurrence

All occurrences are in the same part the target is located in.

| row | driver / measurement | occurrence in that part | state the source requires |
|---|---|---|---|
| `0000027904-26-000020#019` | pre-tax income, GAAP | `Pre-tax (loss)/income (214) 320 (534) NM` in the `1Q26 1Q25` GAAP table | `decreased` |
| `0000092380-26-000044#038` | diluted EPS | `Diluted $ 0.45 $ (0.26) n.m.` | `increased` |
| `0000092380-26-000044#039` | fuel cost per gallon | `Fuel costs per gallon, including fuel tax $ 2.73 $ 2.49 9.6` | `increased` |
| `0000898173-26-000006#052` | store count, domestic | `Ending domestic store count` line: `6,447 6,265 6,447 6,265` | `increased` |
| `0000898173-26-000006#053` | shareholders' equity | `(763,352)` then `(1,370,961)` under the two December dates | `increased` |
| `0001041061-26-000003#077` | EPS excluding Special Items | `EPS Excluding Special Items $1.73 $1.61 +8` | `increased` |
| `0001104659-25-102611#096` | sales mix, failure and maintenance | `a slight increase in the maintenance and failure categories` | `increased` |
| `0001104659-26-017090#112` | net income, adjusted | `Adjusted net income (non-GAAP) $ 48,305 $ 51,785 $ 182,961 $ 168,679` | `decreased` |
| `BBY_2026-03-03T08.00#142` | operating margin, adjusted | `both of which are slightly up to last year`, and separately `increased 10 basis points compared to last year` | `increased` |

Six of these are new against my 2125 report and each is new **because the
window hid it**, not because the rule moved: the comparative table or the
direction sentence sits outside 700 characters of the located quote.

**Your two 2126 rulings are applied, not re-argued.** `#142` stands, and the
complete part now supplies same-driver, same-adjusted-measurement, same-quarter
direction outright, so the target-restriction doubt I recorded in 2125 is
withdrawn. `#096` is a correction, not unresolved: 4.3 is first match wins with
stated direction first, "no fundamental shifts" does not deny a slight increase,
and the next sentence states the increase for this driver. The older-than-
prior-year window may force a null `comparison_baseline` under 7.1; that is a
different field and no reason to discard a source-stated direction.

### Apparent comparisons that are outside the fact's meaning

Recorded rather than used, as you asked:

- `0000027904-26-000020#021` — the part states a per-share prior only for the
  **GAAP** measure. This fact is the non-GAAP per-share figure listed under the
  non-GAAP results, so that prior is a different measurement. No adjusted
  per-share prior is stated anywhere in the part. Supported.
- `AAL_2026-04-23T08.30#134` — the only adjusted per-diluted-share comparison in
  the part is **forward guidance for the next quarter**, a guidance expectation
  and not a temporal prior. Supported.
- `MCD_2026-02-11T16.30#171` — the value is referenced again only in a forward
  statement about expanding from it next year: a guidance expectation, not a
  prior of this fact. Supported.

The remaining 23 supported rows state no prior-period value and no direction for
their exact driver, measurement, population and period anywhere in the complete
part — covenant thresholds and facility terms, one-off charges, ownership and
concentration shares, and counts stated once. No state was taken from a
different driver, a different slice, a guidance expectation, or arithmetic on
unrelated figures, and no EPS direction was inferred from an unspecified
"earnings" direction.

---

## 2. The procedural source-task clarification

**What is wrong with the task as served.** The located-target paragraph tells
the reviewer that the target names the one meaning to interpret and that the
complete event is context "so you can interpret those targets correctly". It
never says that the context is evidence for the reviewer's own **fields**. Nine
times out of thirty-five the reviewer read the located quote as bounding the
state judgement and returned a bare-value state while the same part stated the
prior value or the direction. That is an input defect, not a rule defect: 4.3
already scopes the metric state to the source and is already ordered.

**The smallest change: one sentence added to the existing target-role
paragraph.** Insert immediately after `Interpret those targets only.` and before
the sentence that caps the split. Nothing else changes; no second state rule is
created; the field-specific quote restrictions and the ordered rules stand
exactly as they are. My proposed wording:

> The target fixes WHICH fact you review, not which part of the source may
> evidence it: unless a field's own rule restricts that field to the quote,
> read the complete supplied source when you fill it, and apply the ordered
> rules in the order they are written.

**Why this corrects the demonstrated defect.** It names the one thing the
reviewer got wrong — the scope of the *evidence*, not the scope of the *target*
— and it names it once, generically, for every field at once. It leaves the
quote-restricted fields restricted by their own rules, so nothing that is
currently narrow becomes wide. It adds no state vocabulary, no proximity test
and no second ordering. It is workflow wording, carries no company, number,
example, expected decision or grader-derived material, and it is equally true
for a target whose part states no prior at all.

**Not implemented, and no call prepared.**

---

## 3. Period question

Withdrawn on your ruling and not pursued. I accept that consistency between two
key examples is not correctness proof, and that `#048` carries percent LEVEL
operands while `#115` carries percent_yoy CHANGE measurements, so `#115`'s
prior-year rates are not the sales-level operands under its current growth
rates and must not be copied into `comparison_*` by analogy. My "say whether"
sentence posed a question rather than resolving a rule and is withdrawn. I
propose no period wording, amend nothing in 5.1 or 6.2, and leave the bounded
period-emission question with you.

---

## 4. Scope

35 rows judged over their complete parts; the 2125 inventory, dispositions and
report are preserved untouched and are superseded only on the state
dispositions. I inspected the metric `driver_state` field only — no other
field, no other fact type, no production code, no new framework. Files written:
this one, `inventory_full_part_2126.py`, `FULL_PART_SEARCH_2126.json` and
`SOURCE_STATE_DISPOSITIONS_2126.json`.
