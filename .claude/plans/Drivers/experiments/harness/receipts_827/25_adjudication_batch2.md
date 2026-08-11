# #827 Stage 3 — adjudication batch 2

**Owner:** `driver/relocation/inline_html.py` · `_parse_context`
**Rules:** 23 of 2,863 non-evidence rules — every one listed, none dropped.
Rows from `22_decision_rules.json`; line numbers are the owning statement.

**Verdicts:** `standard` · `contract` · `mechanical` · `replace` · `unresolved`.

**The batch-1 lesson is applied here:** a generic section number does not
certify a hand-picked membership. Each membership below is shown to be the
STANDARD'S OWN CONTENT MODEL — the exact children the schema declares — not a
list someone chose. Where that cannot be shown, the row stays unresolved.

**Checked first, because it decides everything else:** every element name in
this owner is used as an EXPANDED-NAME PAIR — `_kids(context, I, 'entity')`,
`_only(period, (I,'instant'), …)`, `(D,'explicitMember')` — where `I` is
`_INSTANCE_NS` and `D` is `_DIMENSION_NS`. None of them is matched as prefixed
text, so none is a prefix rule. That is what makes them citable at all.

---

## standard — the XBRL 2.1 context content model

Authority for all of these: **XBRL 2.1**, Recommendation 2003-12-31 +
Corrected Errata 2013-02-20, §4.7 (`xbrli:context`), and **XBRL Dimensions
1.0**, Recommendation 2012-01-25, §3.1.4–3.1.5 for the members.
Spec: `https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html`

| line | rule | why the MEMBERSHIP is the standard's, not a choice |
|---|---|---|
| 567, 603 | `context` children — `entity`, `period`, `scenario` | the `xbrli:context` complexType declares exactly this sequence, `scenario` optional. The set is the content model enumerated; adding or removing a name would contradict the schema |
| 572–573, 605 | `entity` children — `identifier`, `segment` | the `xbrli:entity` complexType: one `identifier`, optional `segment` |
| 579–582, 607 | `period` children — `instant`, `startDate`, `endDate`, `forever` | the `xbrli:period` choice: `(startDate, endDate)` \| `instant` \| `forever`. All four names appear because all four are the declared alternatives |
| 577–578 | reading `explicitMember` / `typedMember` out of a box | XBRL Dimensions 1.0 §3.1.4–3.1.5 — these two ARE the dimension members. Reading them is lawful; the row below is about REFUSING everything else |
| 568 | `scenario` | same context content model; kept separate because it is optional |
| 583, 615 | `placed` — the union of the names above | DERIVED from the same content model, and used to prove nothing was left unplaced. It restates no new rule |
| 644 | the `dimension` attribute | XBRL Dimensions 1.0 — `xbrldi:explicitMember/@dimension`, the axis QName |
| 616–618 | `_ordered(...)` — context, entity, period sequences | the schema declares these as `xs:sequence`, so ORDER is normative, not a preference |

### the cardinality numbers

| line | rule | authority |
|---|---|---|
| 569, 574, 592 | `1` and `0` — exactly one entity, one period, at most one scenario/segment | the same content model's `minOccurs`/`maxOccurs`. These are not thresholds; they are the declared occurrence bounds |
| 571, 625 | `[0]` — taking the single declared child | an index into a set already proven to hold exactly one, by the check on the line above it. Mechanical consequence, not a rule |

## contract — the product's own record shape

| line | rule | authority |
|---|---|---|
| 680 | the returned keys — `period`, `dims`, `dims_expanded`, `typed`, `entity` | the internal context record this module hands its callers. `dims` (written spellings) vs `dims_expanded` (identity) is the split ruled in this round; the frozen public contract publishes only the spellings |

---

---

## replace — L610 · `_only(box, explicitMember, typedMember)`

**I classified this as the standard's content model. It is not, and the
reviewer was right to reopen the batch.**

XBRL 2.1 defines `xbrli:segment` and `xbrli:scenario` as **OPEN** context
components — `xs:any`, namespace `##other`. XBRL Dimensions 1.0 **§3.1.4.4**
says in terms that not every element inside a `segment` or `scenario` is
necessarily a dimension element, and the Segment and Scenario Filters 1.0
Recommendation defines non-XDT content outright.

* `https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html`
* `https://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html`
* `https://www.xbrl.org/specification/segmentscenariofilters/rec-2009-06-22/segmentscenariofilters-rec-2009-06-22.html`

So this row is a hand-written restriction the standard does not impose. My
"the membership is the content model" test — which is the right test — I
applied to the four sets where it holds and then extended it to a fifth where
it does not.

**Reproduced through the public door:**

| `xbrli:segment` contains | verdict |
|---|---|
| an `explicitMember` only | `ok` |
| a lawful non-XDT element only | `malformed_context_structure` |
| an `explicitMember` **plus** lawful non-XDT | `malformed_context_structure` — the dimensional fact is lost too |

**Measured cost, and a correction to my own first measurement:** my first scan
reported 543 of 1,769 filings carrying non-XDT content. That was WRONG — it
counted typed-member *contents* (`…Axis.domain`), which are nested inside
`xbrldi:typedMember`, as if they were direct children. Re-measured with the
members removed first: **0 of 1,769** filings have a direct non-XDT child of
`segment`/`scenario`. Zero measured cost today — and per the permanent rule a
census prices a rule, it never makes one lawful.

**What is actually wrong is the REASON, not the refusal.** Refusing is
defensible while the product contract cannot represent non-XDT content, and it
correctly does not IGNORE that content (ignoring would merge two distinct
contexts into one). But calling well-formed, lawful markup
`malformed_context_structure` is untrue. It needs a truthful
`unsupported_non_xdt_context`, with refuse/allow tests and an isolated
mutation. NOT YET CHANGED — reproduced only.

---

## batch totals — CORRECTED

| verdict | rules |
|---|---|
| standard | 19 |
| contract | 1 |
| mechanical | 2 |
| **replace** | **1** |
| unresolved | 0 |
| **total** | **23** — the complete owner |

My earlier "zero findings, and that is a real result" claim is **withdrawn**.
The owner was not clean; I had certified a restriction the standard does not
impose. The lesson is narrower than "look harder": I had the right test and
stopped applying it one row early.

*(A paragraph here previously said "nothing to change in this owner" and called
that a real result. It is deleted: it contradicted the corrected finding above
it. The instinct — that a clean owner is worth recording — is fine; asserting
one before the certifying rows had been tested as hard as the refusing rows is
not.)*
