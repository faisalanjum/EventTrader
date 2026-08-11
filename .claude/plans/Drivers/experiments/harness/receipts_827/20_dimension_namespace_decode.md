# 20 — Decoding the Dimension/Member namespace from the frozen storage contract

**Reviewer decision (SEQ 47), after the contract gap was reported at SEQ 20.**

## The gap

`Concept` persists `namespace` explicitly. `Dimension` and `Member` do NOT —
`XBRL/xbrl_dimensions.py:107` (read-only) composes

    u_id = company_id + ':' + namespaceURI + ':' + qname

and the persisted property dicts carry `u_id`, `qname`, `label` and friends, but
no namespace. So the namespace exists in the graph only inside that composite.

## Why decoding it is reading a contract, not guessing

**Neither boundary is inferred:**

* the FIRST colon is the company-id boundary — a contract Core already owns and
  relies on in `driver_neo4j_adapter._norm_uid`, which does exactly
  `u_id.partition(":")`;
* the SUFFIX is the record's own exact `qname`, supplied by the record itself.

Every character between them is the namespace URI. The colons INSIDE that URI
are never a delimiter anyone has to interpret, because both ends are known.

This adds no dependency on `XBRL/**` — nothing is imported and nothing there is
changed (`git status XBRL/` = 0 entries throughout).

## The one owner

`driver/core/driver_neo4j_adapter.namespace_from_uid(u_id, qname)`. No regex, no
URI parser, no prefix table, no substring search, no duplicated slice. It
publishes `axis_namespace` / `member_namespace` beside the existing qnames and
label; `u_id` itself is never exposed or compared downstream.

**Fail-closed on every component.** Any violation returns `None` and the pair
goes down the existing truthful exclusion path (`dimension_definition_unresolved`)
rather than binding on an invented namespace:

| input | result |
|---|---|
| `'nocolon'` (no company boundary) | `None` |
| `':x:a:b'` (blank company) | `None` |
| `'1:a:b'` with a qname that is not its suffix | `None` |
| `'1::a:b'` (blank namespace) | `None` |
| `None` | `None` |
| qname `''` (no usable local part) | `None` |

## Full-population storage-compatibility proof (read-only)

Every current record decoded, and the decoded parts reassembled into exactly the
stored value:

| kind | total | decode | `company + ':' + namespace + ':' + qname` == stored |
|---|---|---|---|
| Dimension | 955,960 | 955,960 | **955,960** |
| Member | 1,499,049 | 1,499,049 | **1,499,049** |
| **total** | **2,455,009** | **2,455,009** | **2,455,009** |

The standard decides what QName identity IS. This census only verifies that the
storage shape is compatible with reading it — it prices the rule, it does not
define it.
