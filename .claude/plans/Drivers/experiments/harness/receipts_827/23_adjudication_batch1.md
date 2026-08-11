# #827 Stage 3 — adjudication batch 1

**Owner:** `driver/relocation/inline_html.py`, module level (`<module>`)
**Rules in this owner:** 22 of 1,788 production rules — every one listed below,
none dropped. Rows come from `22_decision_rules.json`; line numbers are the
owning statement.

**Verdicts:** `standard` (official normative source, cited) · `contract`
(frozen owner-approved product value) · `mechanical` (decides no XML/XBRL/SEC
meaning) · `replace` (a rule that must stop being a fixed value).

No code was changed for this batch. `replace` rows are findings, and each one
already has a reproduced public failure and lawful twin, or is explicitly
marked as not yet reproduced.

---

## standard — official normative values

Each row cites the document, its version/date, its section, and the literal
official URL. A title or a code comment is not authority.

| line | rule | authority |
|---|---|---|
| 312 | `_INSTANCE_NS` | **XBRL 2.1**, Recommendation 2003-12-31 + Corrected Errata 2013-02-20, §4.7 — instance namespace `http://www.xbrl.org/2003/instance`. Spec: `https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html` |
| 313 | `_DIMENSION_NS` | **XBRL Dimensions 1.0**, Recommendation 2012-01-25, §2 — `http://xbrl.org/2006/xbrldi`. Spec: `https://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html` |
| 314 | `_INLINE_NS` | **Inline XBRL 1.1**, Recommendation 2013-11-18, §3 — `http://www.xbrl.org/2013/inlineXBRL`. Spec: `https://www.xbrl.org/specification/inlinexbrl-part1/rec-2013-11-18/inlinexbrl-part1-rec-2013-11-18.html` |
| 318 | `_XML_PREFIX_NS` | **Namespaces in XML 1.0 (Third Edition)**, W3C Rec 2009-12-08, §3 — the `xml` prefix is bound by definition to `http://www.w3.org/XML/1998/namespace` and MUST NOT be declared otherwise. Spec: `https://www.w3.org/TR/2009/REC-xml-names-20091208/#ns-decl` |
| 442 | `SEC_CIK_SCHEME` | **EDGAR Filer Manual Volume II**, the `xbrli:identifier/@scheme` value `http://www.sec.gov/CIK` required for the registrant identifier. Source: `https://www.sec.gov/info/edgar/edmanuals.htm` — ⚠ the exact volume/section for the effective acceptance date is still to be pinned; treat as PROVISIONAL until then |
| 446 | `XML_S` | **XML 1.0 (Fifth Edition)**, W3C Rec 2008-11-26, §2.3 — `S ::= (#x20 | #x9 | #xD | #xA)+`. Exactly these four; deliberately NOT Python `.strip()`, which also eats NBSP and zero-width space and would silently normalise a padded CIK into a clean one. Spec: `https://www.w3.org/TR/2008/REC-xml-20081126/#NT-S` |
| 845 | `_ATTR_WS` | **XML 1.0 (Fifth Edition)**, §3.3.3 — attribute-value normalisation replaces each `S` character with `#x20`. Spec: `https://www.w3.org/TR/2008/REC-xml-20081126/#AVNormalize` |
| 874 | `_COLLAPSED` | XML Schema Part 2 Second Edition §4.3.6 `whiteSpace = collapse`, applied to the attributes whose types are QName/NCName/etc. The membership is the standard's consequence, not a taste |

**Withdrawn from this group after review (SEQ 81):** `_COLLAPSED`, `_CONSUMED`
and `_XML_INT` were listed here on a generic citation. A generic facet or a
broad section number does not certify a MANUALLY CHOSEN MEMBERSHIP — the
membership is the rule. They move to *unresolved* below.

## contract — frozen product values

| line | rule | why it is the contract, not a standard |
|---|---|---|
| 260 | `NOT_WELL_FORMED` | an outcome word the channel reads; owned by the frozen contract |
| 829 | `VIEWS_DISAGREE` | same class — a refusal reason, not an XML rule |
| 1623 | `SOURCE_EVIDENCE_KEYS` | the packet's evidence field names |
| 1625 | `PIECE_KEYS` | the packet's piece field names |
| 1626 | `PIECE_KINDS` | the packet's piece kinds |

**Withdrawn from this group (SEQ 81):** `_GRAPH_NUMBER` moves to *unresolved*.
Asking the owner to ratify a corpus-shaped regex would launder a measurement
into a law. The storage contract must be derived from the writer's exact
behaviour, which is **`XBRL/xbrl_reporting.py:77`** (verified on disk; I had
cited `xbrl_dimensions.py`, which is wrong):

```python
self.value = None if self.model_fact.isNil else (
    self.model_fact.sValue if self.model_fact.isNumeric
    else self._extract_text(self.model_fact.value))
```

So numeric `Fact.value` is Arelle's `sValue` under the one pinned version,
plus the graph property type. The 12.4M-fact census stays a compatibility
check only.

## mechanical — decides no XML/XBRL/SEC meaning

| line | rule | note |
|---|---|---|
| 58 | `'ignore'` | a `warnings.filterwarnings` action word |
| 824 | `_Fact` | namedtuple type and field names |

**Withdrawn from this group (SEQ 81):** `_SPAN_TAGS` moves to *unresolved*. I
called it appearance-only, but the spans it computes decide visible headings
and row text, which become the quote and the evidence — so it can change what
attaches. "It only affects rendering" is not true when the rendering IS the
evidence.

## replace — fixed values that must stop deciding

### 1522 · `_KNOWN_FMT`, and the `ixt:fixed-zero` comparison at 1580

`{'', 'ixt:num-dot-decimal', 'ixt:numdotdecimal'}` matches a PREFIX SPELLING.
A prefix is the filing's private alias; `format` is an `xsd:QName` and must be
resolved to its expanded name at the fact, then checked against the official
Transformation Registry namespace URIs (Inline XBRL 1.1 §10; registries 2010,
2011, 2015, 2020-02-12, 2022, plus the SEC approved list).

**Reproduced through `locate`, one filing, only the declaration varied:**

| declaration | expected | actual |
|---|---|---|
| `ixt` → the official 2020-02-12 registry | bind | binds ✅ |
| `ixt` → a bogus non-registry URI | **refuse** | **binds** ❌ |
| `t` → the official 2020-02-12 registry | **bind** | **refuses** ❌ |

Second defect in the same rule: `''` (no `format` attribute) and an explicit
`format=""` are the same member, so an empty declared transformation is read as
"no transformation".

**BLOCKED, not deferred:** the handoff prefers a thin adapter over Arelle's
registry rather than a second registry here, but `requirements.txt` pins
`arelle==2.2` **and** `arelle-release==2.35.0` while the environment has
`arelle-release==2.38.20`, and I may not change dependency pins. Awaiting the
ruling: pin-and-adapt, or admit only the official Recommendation registry URIs
as a small standards-cited table.

### 1520 · `_NUM_DOT` — coupled to the same finding

The printed-number grammar the transformation is expected to produce. It is
correct ASCII syntax today, but it is a hand-written grammar standing in for
whatever the DECLARED registry version actually permits, and the same local
name can have version-specific valid input. It is not independently wrong; it
must move with `_KNOWN_FMT` and is listed so the two are decided together
rather than one being fixed and the other left behind.

### ~~130 · `_EDGE_MARKERS`~~ — RECLASSIFIED `contract`, no change needed

I listed this as a sample-shaped rule to remove. An independent ledger check
found its exact frozen authority, which I had not looked for:

> `.claude/plans/Drivers/WIP/Core_PreparedFactV2_818_827_Audit_2026-07-27.md`
> — the 2026-07-28 decision block *"Fiscal final exact-slice receipt and
> parenthetical measurement"*, immediately followed by *"Core parenthetical
> correction"* and the final Fiscal parity.

That block requires ONE private owner for the existing edge-decoration set,
forbids expanding it into a punctuation catalogue, pins its use to SELECTION
only, and preserves stored evidence exactly. The frozen 1,722-file /
2,023,157-fact parity is recorded there.

So it is a frozen product value with a named decision, not a guess. **No code
change.** The lesson for the rest of this audit: "I could not trace it" is a
statement about my search, not about the value.

---

---

## unresolved — listed as findings, no verdict claimed

### 37 · `_XML_INT` — lawful-but-unrepresentable is reported as malformed

`xs:integer` has an UNBOUNDED lexical space (XML Schema Part 2 §3.3.13), but
CPython refuses `int()` on a digit string longer than
`sys.get_int_max_str_digits()` (4300 here). `xml_integer` catches that and
returns `None`, and the caller turns every `None` into `malformed_scale`.

**Reproduced through `element_evidence`, one filing, only the scale varied:**

| scale attribute | lexically lawful? | verdict | correct? |
|---|---|---|---|
| `6` | yes | `ok` | ✅ |
| a 4,301-digit integer | **yes** | `malformed_scale` | ❌ lawful, merely unrepresentable |
| `6.9` | no | `malformed_scale` | ✅ |

So a filing that wrote something LEGAL gets the same answer as one that wrote
something ILLEGAL. The file already draws this distinction elsewhere for
periods (`unbindable_period` vs `malformed_period`), so the vocabulary and the
precedent exist; the scale path simply never got it.

Before keeping a private regex at all, the standards-complete datatype owner
has to be evaluated — carried with the Arelle pin question below.

### 874 · `_COLLAPSED` — the membership is the rule

Citing `whiteSpace = collapse` (XML Schema Part 2 2e §4.3.6) justifies the
ACTION, not the eight chosen members. Required before any verdict: an exact
per-member type/source map, and a two-way test proving every consumed
collapse-typed attribute is present and every preserve-typed attribute is
absent — `sign` in particular, whose value is a pattern-restricted string.
Otherwise it is replaced by the standards-aware reader.

### 835 · `_CONSUMED` — same class

A broad §10.1 citation does not prove these seven are ALL the
identity/value-affecting attributes this bridge consumes. Required: equality
proven both ways against the attributes actually consumed, and each member
mutation-isolated. Not assumed exhaustive.

### 152 · `_SPAN_TAGS` — can change evidence

Needs a frozen product authority, or replacement by structural HTML behaviour,
with a public failure and lawful twin. Not yet reproduced.

### 1533 · `_GRAPH_NUMBER` — derive from the writer, not the corpus

See the note above.

*(A "duplicated `d = Decimal(...)` in `parse_raw`" was recorded here and is
RETRACTED: there is exactly one, at `inline_html.py:1555`. The apparent
duplicate was an artefact of two overlapping `sed` ranges sharing a boundary
line — a reminder that a finding read out of stitched output is not a finding.)*

---

## batch totals

| verdict | rules |
|---|---|
| standard (cited exactly) | 7 |
| contract | 5 |
| mechanical | 2 |
| replace (reproduced) | 3 |
| **unresolved** | **5** |
| **total** | **22** — the complete owner, nothing omitted |

Six rows moved out of a verdict after review. Recording them as unresolved is
the point: a verdict backed by a generic citation is a guess with a footnote.
