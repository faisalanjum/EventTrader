"""F7 (#827): THE adapter/consumer interface — the ONE statement of the
column names a graph fact row carries between driver_neo4j_adapter (the
writer) and xbrl_attach (the reader).

WHY A BOUNDARY MODULE (the `public_contract.to_public` precedent): the
consumer is forbidden by the write-isolation law (G18) from importing any
neo4j-named module, and the producer must not import its consumer, so the
shared names live where BOTH may look. The adapter\'s emission is proven
equal to this statement by the round-trip node through the public door;
xbrl_attach\'s checked row binds to these same objects.

`decimals` is deliberately absent: it was selected and emitted yet read by
NO consumer (the checked row dropped it by name) — the returned-but-unread
surface this audit removes.
"""

GRAPH_FACT_ROW_FIELDS = ("period_type", "start_date", "end_date", "dims",
                         "fact_id", "context_id", "unit_ref", "unit_name",
                         "is_divide", "value",
                         "concept_namespace", "graph_concept_qname")

#: A dimension\'s five columns: both qnames, the label, both namespace URIs.
GRAPH_DIM_FIELDS = ("axis", "member", "label",
                    "axis_namespace", "member_namespace")


# ---------------------------------------------------------------------------
# EU-007 (#827): THE GRAPH STORED-SPELLING CLAUSE. The tuples above name the
# COLUMNS; this names how the graph SPELLS the values inside them, resolved
# here at the F7 boundary owner so neither side restates it:
#   value      — the writer EMITS the grouped string ("4,824,698,000"), and
#                "0"/"-0" is the ONE lawful two-spelling pair (SEQ 268). That
#                is what the graph STORES; it is NOT a reader-side rejection
#                authority. The reader's lexical owner is XSD decimal, reused
#                through Arelle's pinned decimalPattern — there is no
#                project-authored production regex — so ungrouped "726000000",
#                "+1234" and "01234" are LAWFUL input. A comma-bearing
#                spelling is outside XSD and is admitted only when it
#                round-trips exactly through the runtime's canonical grouped
#                formatting at the input's stated precision.
#                (EU-007 corrected by GRAPH-DECIMAL, #827.)
#   is_divide  — EXACTLY the strings '0' and '1'
#                (exact_numbers.ROUTE_A_BOOLS); Python ints and bools are
#                not graph spellings and abstain everywhere.
#   unit_name  — a divide unit's stored name is numerator+denominator
#                CONCATENATED with NO separator (iso4217:USDshares); a
#                plain unit's name is its single measure; the spelling is
#                decided by NAMESPACE at the writer, never by prefix text.
#   identity-anchor hashes — sha256 over the text encoded ONCE as
#                UTF-8 with 'surrogatepass' (a lone surrogate must not
#                crash hashing; both views hash the same bytes).
#   dates      — exactly [0-9]{4}-[0-9]{2}-[0-9]{2}
#                (exact_numbers._STRICT_ISO): the XSD-1.0 §3.2.9.1 x CPython
#                date intersection, deliberately narrower than xs:date;
#                stored period ENDS are EXCLUSIVE (+1 day); an instant's
#                unused end is the adapter-owned "null" alias (F5 — the
#                door emits None).
# ---------------------------------------------------------------------------
