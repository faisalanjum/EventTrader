# #822 — fresh read-only graph census (saved receipt)

**Taken:** 2026-07-28 · **Access:** read-only Cypher, zero writes
**Why it exists:** the rules added in #822 (repeated-axis refusal, strict date
shapes, Dimension-vs-Member kind checking, Member-label requirements) each
constrain real data. A rule justified only in a code comment is a claim; this
file is the measurement behind it, so its recall cost is auditable and a later
reader can re-run the exact query rather than trust the prose.

---

## 1. Does any real context repeat a dimension axis?

```cypher
MATCH (c:Context) WHERE size(c.dimension_u_ids) > 1
UNWIND c.dimension_u_ids AS du
WITH c, count(du) AS total, count(DISTINCT du) AS distinct_axes
WITH sum(CASE WHEN total <> distinct_axes THEN 1 ELSE 0 END)
       AS contexts_repeating_an_axis,
     count(*) AS multi_axis_contexts
RETURN multi_axis_contexts, contexts_repeating_an_axis
```

| multi_axis_contexts | contexts_repeating_an_axis |
|---|---|
| **2,206,183** | **0** |

**⚠ WHAT THIS QUERY DOES AND DOES NOT PROVE — corrected 2026-07-28.** An earlier
version of this section read "the live graph agrees without exception", which
overstated it. The query compares `dimension_u_ids`, i.e. **ids**. The rule in
code compares **axis qnames**. Those are not the same thing:

```cypher
MATCH (d:Dimension) WITH d.qname AS q, count(DISTINCT d.id) AS ids
RETURN count(*) AS distinct_qnames,
       sum(CASE WHEN ids > 1 THEN 1 ELSE 0 END) AS qnames_with_MULTIPLE_ids,
       max(ids) AS worst_case
```

| distinct_qnames | qnames_with_MULTIPLE_ids | worst_case |
|---|---|---|
| 2,344 | **2,053** | **3,173** |

Dimension ids are per-company, so one axis qname legitimately has thousands of
ids. Distinct ids therefore do **not** imply distinct qnames, and query 1 alone
could not support the rule.

**The measurement that does** — resolving each context's dimension ids to their
qnames (with the same cik-normalisation the adapter applies) and checking those
for repeats:

```cypher
MATCH (c:Context) WHERE size(c.dimension_u_ids) > 1
WITH c LIMIT 200000
UNWIND c.dimension_u_ids AS du
WITH c, split(du, ':')[0] AS dcik, du
WITH c, toString(toInteger(dcik)) + substring(du, size(dcik)) AS ndu
MATCH (d:Dimension {id: ndu})
WITH c, count(d.qname) AS resolved, count(DISTINCT d.qname) AS distinct_qnames
RETURN count(*) AS contexts_examined,
       sum(CASE WHEN resolved <> distinct_qnames THEN 1 ELSE 0 END)
         AS contexts_where_QNAMES_repeat
```

| contexts_examined | contexts_where_QNAMES_repeat |
|---|---|
| **200,000** (a SAMPLE, not the full 2,206,183) | **0** |

**Reading, stated at its true scope:** no context repeats a dimension **id**
(full population), and no context in a **200,000-context sample** resolves to a
repeated axis **qname** — which is the property the code actually tests.
Refusing a repeated axis therefore costs zero recall on everything measured, and
an unseen shape parks. The remaining ~2.0M multi-axis contexts are unmeasured;
that is a sampling bound, not a claim about them.

## 2. What shapes do stored Period dates actually take?

```cypher
MATCH (p:Period)
RETURN count(*) AS periods,
  sum(CASE WHEN p.start_date =~ '[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN 1 ELSE 0 END)
    AS start_strict_iso,
  sum(CASE WHEN p.end_date =~ '[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN 1 ELSE 0 END)
    AS end_strict_iso,
  sum(CASE WHEN p.end_date = 'null' THEN 1 ELSE 0 END) AS end_literal_null
```

| periods | start_strict_iso | end_strict_iso | end_literal_null |
|---|---|---|---|
| **11,416** | **11,415** | **8,358** | **3,058** |

**Reading:** `8,358 + 3,058 = 11,416` exactly — every stored `end_date` is
either a strict ISO date or the literal four-character string `"null"`. There is
no third shape.

### 2b. The instant claim, proved directly rather than inferred

The totals above only *suggest* that instants are the `"null"` ones, by matching
counts. This grouped query proves it in one step, so the claim the code relies on
is independently reproducible:

```cypher
MATCH (p:Period)
RETURN p.period_type AS period_type, count(*) AS periods,
  sum(CASE WHEN p.end_date = 'null' THEN 1 ELSE 0 END) AS end_literal_null,
  sum(CASE WHEN p.end_date =~ '[0-9]{4}-[0-9]{2}-[0-9]{2}' THEN 1 ELSE 0 END)
    AS end_strict_iso,
  sum(CASE WHEN p.end_date IS NULL THEN 1 ELSE 0 END) AS end_real_null
ORDER BY period_type
```

| period_type | periods | end_literal_null | end_strict_iso | end_real_null |
|---|---|---|---|---|
| duration | 8,358 | 0 | **8,358** | 0 |
| instant | 3,058 | **3,058** | **0** | 0 |

**Reading:** every instant carries the literal `"null"` and **not one carries a
date** (`end_strict_iso = 0` on that row) — and every duration carries a real
date. The lawful set for an instant's unused `end_date` is therefore exactly two
forms: `"null"` or absent. An earlier version of this section also allowed a real
date there; that permitted a shape the graph does not have, and it contradicted
the code once the rule was corrected.

## 3. The one malformed Period — and a correction to the audit

```cypher
MATCH (p:Period) WHERE p.start_date = '224-04-01'
MATCH (f:Fact)-[:HAS_PERIOD]->(p)
RETURN count(f) AS facts_total,
       sum(CASE WHEN f.is_numeric='1' AND f.is_nil='0' THEN 1 ELSE 0 END)
         AS numeric_non_nil
```

| bad_start | facts_total | numeric_non_nil |
|---|---|---|
| `224-04-01` | **34** | **34** |

**CORRECTION.** `Core_PreparedFactV2_818_827_Audit_2026-07-27.md` finding B
records this as *"one malformed value, `224-04-01`, on an orphan Period with
zero facts."* It is not an orphan: it carries **34 facts, all numeric non-nil**.

**Impact of the strict-date rule on them: none.** A malformed date can never
equal a well-formed claim, so those facts failed to bind before the rule and
park after it. What changed is *where* and *why* they park, not *whether*.

## 4. Is any id shared between a Dimension and a Member?

```cypher
MATCH (d:Dimension) WITH collect(DISTINCT d.id) AS dids
MATCH (m:Member) WHERE m.id IN dids
RETURN count(DISTINCT m.id) AS ids_that_are_BOTH
```

Result: **no rows — zero shared ids.**

**Reading:** checking that an axis id resolves to a `Dimension` and a member id
to a `Member` costs nothing today, while closing the path where a member's
qname could be written into the axis position and fabricate an axis.

## 5. Member labels

```cypher
MATCH (m:Member)
WITH count(*) AS members, count(m.label) AS with_label
RETURN members, with_label, members - with_label AS null_labels
```

| members | with_label | null_labels |
|---|---|---|
| **1,499,049** | **1,499,049** | **0** |

**Reading:** `check_member_refs` RECOMPUTES the slice token from the label, so a
Member without one can verify nothing. Requiring a non-blank string label on a
`Member` record costs zero recall. (A `Dimension` record legitimately has a null
label — the query returns `null AS label` for it — so the requirement is
kind-specific, not blanket.)

---

## Standing caveats

These are **evidence snapshots, not permanent assumptions**. Every rule they
justify still keeps its adversarial missing/duplicate/malformed cases even where
the current count is zero — a count of zero is what makes a rule cheap, never
what makes it unnecessary.
