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
