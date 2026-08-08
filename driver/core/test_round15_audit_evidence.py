"""#825 / #828 — the adapter's silent exclusions become visible evidence.

`get_xbrl_fact_dimensions` DROPS rows it cannot read: arrays of unequal length,
and pairs whose Dimension/Member definitions do not resolve. The fail-closed
behaviour is correct and does not change here — what was missing is that the
drop left no trace, so a recall bucket existed that nobody could see or count.

The contract changes ONCE: the read returns verified rows AND immutable
exclusion summaries, per event/concept/reason, with exact counts taken from the
SAME read. No second graph method, no second query, no per-fact spam.

HONEST LABELS. A misaligned array is recorded as exactly that — not as a typed
dimension, which is an unproved cause for the same symptom.
"""
from types import MappingProxyType

import pytest

from driver.core.driver_neo4j_adapter import Neo4jStore

_DIM_QUERY_MARK = "c.dimension_u_ids AS dus"


def _store_reading(rows, definitions=()):
    """A store whose ONE read returns these fact rows, then these definitions."""
    store = Neo4jStore.__new__(Neo4jStore)          # no driver, no connection

    def fake_read(query, **params):
        return list(rows) if _DIM_QUERY_MARK in query else list(definitions)
    store._read = fake_read
    return store


#: A DELIBERATELY SYNTHETIC taxonomy namespace for the adapter-only rows below.
#: `_row` has no document partner — these tests exercise the read/exclusion
#: contract, never a filing — so this value is not claiming any official
#: identity and nothing here needs to agree with a document.
_NS_SYNTHETIC_TAXONOMY = "http://example.org/us-gaap"
CIK10 = "0000000001"        # Company spelling; its archive/node form is "1"


def _row(**over):
    # This is the RAW shape `_read` returns, so it carries the concept identity
    # exactly as the query selects it: the binder compares (namespace URI,
    # local name), and both halves come from the one Concept record.
    r = {"fid": "1", "fact_id": "f1", "context_id": "c1",
         "period_type": "duration", "start_date": "2024-01-01",
         "end_date": "2024-07-01", "unit_ref": "u1", "value": "726",
         "decimals": "0", "unit_name": "iso4217:USD", "is_divide": "0",
         "concept_namespace": _NS_SYNTHETIC_TAXONOMY,
         "graph_concept_qname": "us-gaap:X",
         # CONTEXT SIDE = the ten-digit Company spelling. Every `dus`/`mus`
         # below uses CIK10, whose archive/node form is "1", so the node ids in
         # each definition list stay exactly as they were.
         "company_cik": CIK10,
         "dus": [], "mus": []}
    r.update(over)
    return r


def test_828_a_clean_dimensionless_read_reports_NO_exclusions():
    """The positive control: a clean read must not manufacture a bucket."""
    out = _store_reading([_row(), _row(fact_id="f2", context_id="c2")]) \
        .get_xbrl_fact_dimensions("acc", "us-gaap:A")
    assert len(out.rows) == 2
    assert out.exclusions == ()


def test_828_MISALIGNED_arrays_are_counted_and_honestly_labelled():
    """Two facts in one context and one in another — the counts must be exact
    and distinct, and the label must not claim a cause it has not proved."""
    bad = [_row(fact_id="f1", context_id="c1", dus=[f"{CIK10}:d"], mus=[]),
           _row(fact_id="f2", context_id="c1", dus=[f"{CIK10}:d"], mus=[]),
           _row(fact_id="f3", context_id="c9",
                dus=[f"{CIK10}:d", f"{CIK10}:e"], mus=[f"{CIK10}:m"])]
    out = _store_reading(bad).get_xbrl_fact_dimensions("acc", "us-gaap:A")
    assert out.rows == ()
    assert len(out.exclusions) == 1
    rec = out.exclusions[0]
    assert rec["event"] == "dimension_member_array_misaligned"
    assert rec["where"] == "graph_fact_dimensions"
    assert rec["concept"] == "us-gaap:A"
    assert rec["fact_count"] == 3
    assert rec["context_count"] == 2
    assert "typed" not in rec["event"], "an unproved cause must not be claimed"


def test_828_an_UNRESOLVED_definition_is_its_own_reason():
    """A well-formed pair whose Dimension/Member cannot be resolved is a
    DIFFERENT failure from a misaligned array and must not share its bucket."""
    rows = [_row(fact_id="f1", context_id="c1", dus=[f"{CIK10}:d"], mus=[f"{CIK10}:m"])]
    out = _store_reading(rows, definitions=[]) \
        .get_xbrl_fact_dimensions("acc", "us-gaap:A")
    assert out.rows == ()
    assert [r["event"] for r in out.exclusions] == \
        ["dimension_definition_unresolved"]
    assert out.exclusions[0]["fact_count"] == 1


def test_828_two_reasons_in_one_read_keep_SEPARATE_counts():
    rows = [_row(fact_id="f1", context_id="c1", dus=[f"{CIK10}:d"], mus=[]),
            _row(fact_id="f2", context_id="c2", dus=[f"{CIK10}:d"], mus=[f"{CIK10}:m"])]
    out = _store_reading(rows).get_xbrl_fact_dimensions("acc", "us-gaap:A")
    by_reason = {r["event"]: r for r in out.exclusions}
    assert set(by_reason) == {"dimension_member_array_misaligned",
                              "dimension_definition_unresolved"}
    assert all(r["fact_count"] == 1 for r in by_reason.values())


def test_828_the_summaries_are_IMMUTABLE():
    rows = [_row(dus=[f"{CIK10}:d"], mus=[])]
    out = _store_reading(rows).get_xbrl_fact_dimensions("acc", "us-gaap:A")
    assert isinstance(out.exclusions, tuple)
    with pytest.raises(TypeError):
        out.exclusions[0]["fact_count"] = 99


def test_828_the_return_is_a_NAMED_two_field_value_not_a_bare_list():
    """One named shape, so a caller cannot silently keep treating the result as
    a list of rows and drop the evidence on the floor."""
    out = _store_reading([_row()]).get_xbrl_fact_dimensions("acc", "us-gaap:A")
    assert out._fields == ("rows", "exclusions")
    assert list(out) == [out.rows, out.exclusions]


# ---- #825 (4): menu_tokens is code-owned, and validated BEFORE any I/O ------

from driver.core.prepared_fact_v2 import SchemaError                # noqa: E402
from driver.core.test_round10_event_boundary import (_ACC, _XMLNS, _Counting,   # noqa: E402
                                                     _CountingProvider,
                                                     _door_item, _ns_dim,
                                                     parts_for)
from driver.core.xbrl_attach import attach_event_xbrl               # noqa: E402


def _door(menu_tokens):
    store, provider = _Counting(), _CountingProvider()
    item = _door_item("us-gaap:A", "fA")
    try:
        attach_event_xbrl([item], source_id=_ACC, store=store,
                          filing_provider=provider,
                          text_parts=parts_for([item]),
                          menu_tokens=menu_tokens).facts
    finally:
        _door.spent = (store.representation, store.cik, provider.fetches)


@pytest.mark.parametrize("bad", [
    None, [], ["segment:a"], {"segment:a"}, ("segment:a",),
    frozenset([""]), frozenset(["   "]), frozenset([5]), frozenset([None]),
    frozenset(["ok", 5]), "segment:a",
])
def test_825_malformed_menu_tokens_are_refused_BEFORE_any_io(bad):
    """`menu_tokens` is CODE-owned — the exact immutable output shape of
    `slice_menu.build_menu` — but it is still a parameter of a public door, so
    it is checked like every other input, and checked BEFORE the graph or the
    provider is touched. A mutable set is refused too: the door must not hold a
    container someone else can still edit."""
    with pytest.raises(SchemaError, match="menu_tokens"):
        _door(bad)
    assert _door.spent == (0, 0, 0), "a pure check must cost no I/O"


def test_825_an_empty_frozenset_is_lawful_it_is_not_a_missing_menu():
    out = attach_event_xbrl(
        [_door_item("us-gaap:A", "fA")], source_id=_ACC, store=_Counting(),
        filing_provider=_CountingProvider(),
        text_parts=parts_for([_door_item("us-gaap:A", "fA")]),
        menu_tokens=frozenset()).facts
    assert len(out) == 1


# ---- part-1 repairs: the four gaps the reviewer reproduced ------------------

def test_825_the_graph_result_is_immutable_at_EVERY_level():
    """"Immutable" was true only of the outer namedtuple. `.rows` was a plain
    list of plain dicts whose `dims` were plain lists of plain dicts — so a
    caller could append a row, rewrite a value, or invent a dimension AFTER the
    adapter had verified them. The verification is what makes the rows worth
    anything; a value that can change afterwards carries none of it."""
    rows = [_row(dus=[f"{CIK10}:d"], mus=[f"{CIK10}:m"])]
    defs = [{"id": "1:d", "kind": "Dimension", "qname": "ax:A", "u_id": "1:http://example.org/ax:ax:A", "label": None},
            {"id": "1:m", "kind": "Member", "qname": "mb:M", "u_id": "1:http://example.org/mb:mb:M", "label": "North"}]
    out = _store_reading(rows, definitions=defs) \
        .get_xbrl_fact_dimensions("acc", "us-gaap:A")
    assert len(out.rows) == 1 and len(out.rows[0]["dims"]) == 1
    with pytest.raises((AttributeError, TypeError)):
        out.rows.append({"injected": True})
    with pytest.raises(TypeError):
        out.rows[0]["value"] = "999"
    with pytest.raises((AttributeError, TypeError)):
        out.rows[0]["dims"].append({"axis": "x", "member": "y", "label": "z"})
    with pytest.raises(TypeError):
        out.rows[0]["dims"][0]["member"] = "swapped"





@pytest.mark.parametrize("dus,mus", [
    # BOTH sides the wrong container. `r["dus"] or []` turned every falsey one
    # into an empty list, so a BROKEN array became "no dimensions" and the row
    # was ACCEPTED — worse than a drop, because a dimensionless claim could then
    # match a fact whose real dimensions were merely unreadable.
    ("", ""), (0, 0), (False, False), ({}, {}), ((), ()), (set(), set()),
    (5, 5), ("abc", "abc"),
    # LEFT only.
    (5, []), ({"a": 1}, []), ("string", []), ("", []), (0, []), ((), []),
    # RIGHT only — the guard reads BOTH arrays, and nothing tested this side.
    ([], 5), ([], "string"), ([], ""), ([], 0), ([], ()),
    # the containers are lists, the ELEMENTS are not strings.
    ([5], [6]), ([None], [None]), (["ok"], [7]),
])
def test_825_every_malformed_array_yields_ZERO_rows_and_ONE_exact_record(dus, mus):
    """THE one malformed-array matrix. Two tests used to make this claim with
    five pairs duplicated between them and the assertions written twice; a claim
    with two owners drifts, and one of them had already weakened to asserting
    only that `.rows` is a tuple — true of every outcome, including keeping the
    bad row. What matters is what the read RETURNED and what it RECORDED."""
    out = _store_reading([_row(dus=dus, mus=mus, context_id="c1")]) \
        .get_xbrl_fact_dimensions("acc", "us-gaap:A")
    assert out.rows == (), f"{dus!r}/{mus!r} was accepted as a dimensionless fact"
    assert [r["event"] for r in out.exclusions] == ["graph_row_unreadable"]
    assert out.exclusions[0]["fact_count"] == 1
    assert out.exclusions[0]["context_count"] == 1
    assert out.exclusions[0]["concept"] == "us-gaap:A"

@pytest.mark.parametrize("empty", [None, []])
def test_825_only_NONE_and_the_empty_list_lawfully_mean_no_dimensions(empty):
    """The positive control, so the fix above cannot become 'refuse everything'."""
    out = _store_reading([_row(dus=empty, mus=empty)]) \
        .get_xbrl_fact_dimensions("acc", "us-gaap:A")
    assert len(out.rows) == 1 and out.rows[0]["dims"] == ()
    assert out.exclusions == ()


def test_825_the_positive_control_uses_build_menus_REAL_output():
    """This asserted `"frozenset" in getsource(build_menu)` and then passed a
    hand-written literal — while its own docstring claimed it was not one. The
    gate must accept what the owner ACTUALLY produces, so the owner is called."""
    from driver.core.slice_menu import build_menu
    tokens, _logs = build_menu(
        [{"axis": "srt:StatementGeographicalAxis",
          "member": "srt:NorthAmericaMember", "label": "North America"}],
        used_scopes=())
    assert type(tokens) is frozenset and tokens, "the owner produced no token"
    item = _door_item("us-gaap:A", "fA")
    out = attach_event_xbrl([item], source_id=_ACC, store=_Counting(),
                            filing_provider=_CountingProvider(),
                            text_parts=parts_for([item]), menu_tokens=tokens).facts
    assert len(out) == 1


# ---- gap 3: v1 must not lose the exclusions it just collected ---------------

def test_825_v1_EMITS_member_menu_when_exclusions_exist_with_NO_slice_menu(
        tmp_path):
    """`if menu_tokens is not None:` gated the WHOLE `member_menu`, so a run
    with no slice menu collected the adapter's exclusions into `menu_logs` and
    then dropped them — precisely the second silent-drop gate #828 exists to
    remove. The exclusions must survive; the folds may legitimately be empty."""
    from driver.core.driver_neo4j_adapter import GraphFactRows
    from driver.core.test_driver_write_cli import (FakeStore, audit_docs, fact,
                                                   run)
    excl = MappingProxyType({"event": "dimension_member_array_misaligned",
                             "where": "graph_fact_dimensions",
                             "concept": "us-gaap:Revenues",
                             "fact_count": 7, "context_count": 3})

    class _Store(FakeStore):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            return GraphFactRows(rows=self.xbrl_facts.get(concept, []),
                                 exclusions=(excl,))

    store = _Store(slice_menu={"xbrl_members": [], "used_scopes": []})
    run(tmp_path, [fact(xbrl_concept_raw="us-gaap:Revenues", member_refs=[])],
        store=store)
    docs = audit_docs(tmp_path)
    menus = [d["member_menu"] for d in docs if "member_menu" in d]
    assert menus, "the exclusions were collected and then dropped"
    assert menus[-1]["exclusions"] and \
        menus[-1]["exclusions"][0]["event"] == "dimension_member_array_misaligned"


def test_825_a_completely_clean_no_menu_run_KEEPS_its_minimal_audit(tmp_path):
    """The other half: making exclusions visible must not start emitting an
    empty `member_menu` on every clean run that never built one."""
    from driver.core.test_driver_write_cli import FakeStore, audit_docs, fact, run
    run(tmp_path, [fact()], store=FakeStore())
    assert not any("member_menu" in d for d in audit_docs(tmp_path))


# ---- the two proof gaps: aliasing, and the merged malformed-array matrix ----

def test_825_the_result_is_ISOLATED_from_the_caller_originals():
    """Immutability of the RETURNED object is only half the promise. The other
    half is isolation: if the raw rows, their dimension arrays, or the
    definition records the adapter read can still be edited afterwards, the
    "verified" result changes underneath whoever holds it. Mutating a caller's
    object must not reach the result, and freezing alone never proves that."""
    dus, mus = [f"{CIK10}:d"], [f"{CIK10}:m"]
    raw = _row(dus=dus, mus=mus, value="726", context_id="c1")
    defs = [{"id": "1:d", "kind": "Dimension", "qname": "ax:A", "u_id": "1:http://example.org/ax:ax:A", "label": None},
            {"id": "1:m", "kind": "Member", "qname": "mb:M", "u_id": "1:http://example.org/mb:mb:M", "label": "North"}]
    out = _store_reading([raw], definitions=defs) \
        .get_xbrl_fact_dimensions("acc", "us-gaap:A")
    before = ([dict(r) for r in out.rows],
              [[dict(d) for d in r["dims"]] for r in out.rows])

    raw["value"] = "999"                     # the raw row the reader returned
    raw["context_id"] = "swapped"
    dus.append(f"{CIK10}:extra")                    # its dimension arrays, in place
    mus.append(f"{CIK10}:extra")
    defs[0]["qname"] = "ax:REWRITTEN"        # the definition records
    defs[1]["label"] = "Elsewhere"
    defs.append({"id": "1:x", "kind": "Member", "qname": "q", "u_id": "1:http://example.org/q:q", "label": "l"})

    after = ([dict(r) for r in out.rows],
             [[dict(d) for d in r["dims"]] for r in out.rows])
    assert after == before, "the result moved when the caller's originals did"
    # WHAT THIS CAN AND CANNOT CATCH, stated so a later reader is not misled.
    # It passes on the current code because every value copied out is an
    # IMMUTABLE SCALAR and `dims` is rebuilt, so no shared-object path exists
    # today. Its job is the FUTURE refactor that shares one — and it is not
    # vacuous: aliasing the row to the raw record, or a dim to the definition
    # record, both make it fail (verified by mutation, though those mutations
    # trip the shape assertions above before reaching this comparison).
    assert out.rows[0]["value"] == "726"
    assert dict(out.rows[0]["dims"][0]) == {"axis": "ax:A", "member": "mb:M",
                                            "label": "North",
                                            # THE EXPANDED IDENTITY travels beside the raw qname now: a
                                            # qname alone cannot say WHICH taxonomy an axis belongs to.
                                            # The namespace is decoded from the record's own composite id.
                                            "axis_namespace":
                                                "http://example.org/ax",
                                            "member_namespace":
                                                "http://example.org/mb"}




# ===== #825 PART 2 — one immutable event result, per item ====================
#
# The door returned a bare list built by a comprehension, so the FIRST item to
# raise aborted the whole event and erased every valid sibling. The Channel
# Contract returns an outcome PER ITEM; an item-local failure keeps its index
# and cannot delete an independent neighbour. Event-wide failures still fan out
# to every affected item, and a programming error still aborts loudly.

def _two_item_event(store=None, provider=None, **kw):
    good = _door_item("us-gaap:A", "fA")
    bad = _door_item("us-gaap:A", "fA")
    bad["fact"]["item"]["quote"] = "THIS QUOTE IS NOT IN THE FILING"
    items = [good, bad]
    # NOT `.facts` — these tests consume the RESULT RECORD deliberately; the
    # call-site migration script over-reached into them.
    return attach_event_xbrl(items, source_id=_ACC,
                             store=store or _Counting(),
                             filing_provider=provider or _CountingProvider(),
                             text_parts=parts_for(items), **kw)


def test_825p2_a_bad_item_cannot_erase_a_VALID_SIBLING():
    """THE contract defect. One malformed item aborted the comprehension and
    the whole event returned nothing, so a channel lost facts that were never
    in question."""
    res = _two_item_event()
    assert [i for i, _f in res.facts] == [0], "the valid sibling was erased"
    assert [o["index"] for o in res.preflight_outcomes] == [1]
    assert res.preflight_outcomes[0]["decision"] == "rejected"


def test_825p2_the_result_carries_its_own_source_id():
    """`source_id` travels WITH the facts so the writer can ASSERT the two match
    at handoff. Carrying it ENABLES that check; it cannot by itself stop a caller
    separating them, and the assertion arrives with the switch."""
    assert _two_item_event().source_id == _ACC


def test_825p2_the_whole_result_is_immutable():
    res = _two_item_event()
    with pytest.raises((AttributeError, TypeError)):
        res.facts.append(("x", "y"))
    with pytest.raises((AttributeError, TypeError)):
        res.preflight_outcomes.append({})
    with pytest.raises(TypeError):
        res.preflight_outcomes[0]["decision"] = "written"
    with pytest.raises(TypeError):
        res.member_menu["exclusions"] = ()


def test_825p2_the_outcome_row_equals_the_LIVE_CLI_row_BY_VALUE():
    """Field NAMES matching is not parity. The switch hands these rows to the
    live serializer, so what must match is the value on the wire — including
    `codes` becoming a JSON list, which is where a tuple would have differed."""
    import json

    from driver.core.driver_write_cli import _item, _jsonable
    row = _two_item_event().preflight_outcomes[0]
    live = _item(row["index"], row["decision"], row["codes"],
                 fact_id=row["fact_id"], detail=row["detail"])
    assert json.loads(json.dumps(row, default=_jsonable)) == \
        json.loads(json.dumps(live, default=_jsonable))
    assert json.loads(json.dumps(row, default=_jsonable))["codes"] == \
        ["XBRL_CONTRACT_INVALID"], "codes must serialize as a JSON list"


def test_825p2_EVERY_path_returns_the_same_result_TYPE():
    """Compared against each other, not asserted one at a time: empty,
    all-invalid and populated must be the one shape."""
    from driver.core.xbrl_attach import AttachResult
    empty = attach_event_xbrl([], source_id=_ACC, store=_Counting(),
                              filing_provider=_CountingProvider(), text_parts=[])
    bad = _door_item("us-gaap:A", "fA")
    bad["fact"]["item"]["quote"] = "NOT IN THE FILING"
    invalid = attach_event_xbrl([bad], source_id=_ACC, store=_Counting(),
                                filing_provider=_CountingProvider(),
                                text_parts=[{"part": "fA", "content": "x"}])
    populated = _member_event()
    kinds = {type(r) for r in (empty, invalid, populated)}
    assert kinds == {AttachResult}, kinds
    assert all(r._fields == ("source_id", "facts", "preflight_outcomes",
                             "member_menu")
               for r in (empty, invalid, populated))


@pytest.mark.parametrize("break_it,decision,code", [
    ("count", "parked", "XBRL_BINDING_UNAVAILABLE"),
    ("outage", "parked", "SOURCE_UNAVAILABLE"),
    ("hashes", "rejected", "XBRL_CONTRACT_INVALID"),
])
def test_825p2_a_SHARED_failure_fans_out_to_every_valid_item(break_it, decision,
                                                             code):
    """One cause, every affected item — each keeping its own index. Saved as a
    control rather than left to a live probe."""
    items = [_door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB")]

    class _Store(_Counting):
        def get_xbrl_representation_count(self, source_id):
            self.representation += 1
            return 2 if break_it == "count" else 1

    class _Provider:
        def get_filing_document(self, source_id):
            if break_it == "outage":
                raise OSError("connection reset")
            # UNREACHABLE BY DESIGN: the count and hash guards both fire before
            # the document is fetched, which is itself the "every cheap check
            # before I/O" law. Saying so out loud beats a plausible-looking
            # return that would quietly mask the guard moving.
            raise AssertionError(
                f"{break_it}: the filing was fetched, but this failure must be "
                f"caught before any provider I/O")

    if break_it == "hashes":
        # A hash CONFLICT is between the items THEMSELVES, so break one item's
        # recorded representation rather than the served document. It must stay
        # a plain `dict`: the door requires exactly that type, so wrapping it in
        # a mapping proxy rejected the item on SHAPE in the pure phase — the two
        # hashes then never met, the door fetched the filing, and the test
        # passed on the served-document mismatch instead. Same words, different
        # law. The unreachable-provider guard below is what exposed it.
        items[1]["source_evidence"] = {**dict(items[1]["source_evidence"]),
                                       "representation_sha256": "0" * 64}

    res = attach_event_xbrl(items, source_id=_ACC, store=_Store(),
                            filing_provider=_Provider(),
                            text_parts=parts_for(items))
    assert res.facts == ()
    assert [o["index"] for o in res.preflight_outcomes] == [0, 1]
    assert {o["decision"] for o in res.preflight_outcomes} == {decision}
    assert {o["codes"] for o in res.preflight_outcomes} == {(code,)}


def test_825p2_TWO_concepts_keep_SEPARATE_adapter_summaries():
    """The exclusion counts are per concept. One shared bucket would make the
    recall figure unattributable."""
    from driver.core.driver_neo4j_adapter import GraphFactRows
    from driver.core.test_round10_event_boundary import _door_row

    class _PerConcept(_Counting):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            self.row_reads.append(concept)
            fid = "fA" if concept.endswith("A") else "fB"
            return GraphFactRows(
                rows=[_door_row(fid, concept=concept)],
                exclusions=(MappingProxyType(
                    {"event": "dimension_member_array_misaligned",
                     "where": "graph_fact_dimensions", "concept": concept,
                     "fact_count": 1 if fid == "fA" else 7,
                     "context_count": 1}),))

    items = [_door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB")]
    res = attach_event_xbrl(items, source_id=_ACC, store=_PerConcept(),
                            filing_provider=_CountingProvider(),
                            text_parts=parts_for(items))
    # THE COMPLETE ORDERED SEQUENCE. A dict comprehension collapsed duplicate
    # summaries, so double-counting the same silent drop stayed green — which is
    # precisely the honesty this record exists to provide.
    assert [(x["concept"], x["fact_count"])
            for x in res.member_menu["exclusions"]] == \
        [("us-gaap:A", 1), ("us-gaap:B", 7)]


def test_825p2_caller_mutation_of_a_NON_EMPTY_member_LOG_cannot_reach_the_result():
    """The earlier mutation control only had notes to mutate; a failing member
    check is the path that produces LOGS, and it needs its own control."""
    import driver.core.slice_menu as sm
    escaped = []
    real = sm.check_member_refs

    def capture(*a, **k):
        problems, notes, logs = real(*a, **k)
        escaped.append(logs)
        return problems, notes, logs

    mp = pytest.MonkeyPatch()
    mp.setattr(sm, "check_member_refs", capture)
    try:
        res = _member_event(axis=_SEG, member=_ELIM, part="segment:x")
    finally:
        mp.undo()
    logs = escaped[0]
    assert logs, "the fixture must actually produce a log to mutate"
    logs[0]["event"] = "INJECTED"
    logs.append({"event": "ALSO INJECTED"})
    assert [dict(x) for x in res.member_menu["exclusions"]] == \
        [{"event": "fs20_hard_exclude", "axis": _SEG, "member": _ELIM,
          "where": "current_fact_ref"}]


@pytest.mark.parametrize("raiser,decision,code", [
    ("schema", "rejected", "XBRL_CONTRACT_INVALID"),
    ("production", "parked", "XBRL_BINDING_UNAVAILABLE"),
    ("unavailable", "parked", "SOURCE_UNAVAILABLE"),
])
def test_825p2_the_three_default_mappings_are_pinned(raiser, decision, code):
    """Defaults only — a branch that already owns a more specific code keeps
    it. Nothing here parses an exception MESSAGE to choose."""
    from driver.core.xbrl_attach import _default_outcome
    from driver.core.prepared_fact_v2 import (ProductionValidationError,
                                              SourceUnavailable)
    exc = {"schema": SchemaError, "production": ProductionValidationError,
           "unavailable": SourceUnavailable}[raiser]("boom")
    assert _default_outcome(exc) == (decision, code)


def test_825p2_an_internal_BAD_DECISION_stays_loud_and_is_not_an_assert():
    """The last guard before a decision reaches the channel was an `assert`,
    which `python -O` strips — so under optimisation an internal slip would
    have published a word the channel cannot interpret, silently.

    THE BAD VALUE NOW COMES FROM THE ONLY PLACE IT CAN. There is no `decision`
    parameter left to pass one through, so the fault is injected into
    `OUTCOME_CLASSES` itself — the single owner — which is the real drift this
    guard defends against."""
    import driver.core.prepared_fact_v2 as pfv
    from driver.core.xbrl_attach import _outcome_row
    mp = pytest.MonkeyPatch()
    mp.setitem(pfv.OUTCOME_CLASSES, SchemaError, "not_a_public_word")
    try:
        with pytest.raises(RuntimeError, match="not one of the public decisions"):
            _outcome_row(0, SchemaError("x"))
    finally:
        mp.undo()


def test_825p2_a_PROGRAMMING_error_still_aborts_the_whole_run():
    """Item-local outcomes are caught by CLASS. A KeyError from our own code is
    a bug and must never be converted into an item row."""
    class Buggy(_Counting):
        def get_source_company_cik(self, source_id):
            return {}["missing"]

    with pytest.raises(KeyError):
        _two_item_event(store=Buggy())


# ===== #825 PART 2 — THE SAVED PROOF MATRIX ==================================
#
# WHY THIS SECTION EXISTS. The eleven tests above passed while SEVEN real
# defects stood, because they asserted SHAPE and never CONTENT: the member
# test checked only that the two KEYS existed, and the immutability test only
# ever inspected an EMPTY result, so neither could see the note being thrown
# away or a populated result left unfrozen. Every test below therefore asserts
# an EXACT record, and each has been shown to fail against the defect it names.
#
# The fixture carries a REAL dimension end-to-end: a filing context declaring
# the explicit member, a graph row carrying the same pair, and a fact whose own
# slice token matches the label-recomputed token. Without all three the binder
# abstains long before the member check, and every assertion here would be
# vacuous.

_GEO = "srt:StatementGeographicalAxis"
_SEG = "us-gaap:StatementBusinessSegmentsAxis"
_ELIM = "us-gaap:IntersegmentEliminationMember"
_NON_SLICE = "eqt:DistributionChannelAxis"
_MEMBER, _PART = "geo:M", "geography:us"
_NOTE = {"slice_part": _PART, "member": _MEMBER, "axis": _GEO, "fold": True}


def _dim_doc(axis=_GEO, member=_MEMBER):
    """A filing whose context c2 DECLARES the explicit member being claimed."""
    return (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c2"><xbrli:entity>'
            '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier>'
            f'<xbrli:segment><xbrldi:explicitMember dimension="{axis}">'
            f'{member}</xbrldi:explicitMember></xbrli:segment></xbrli:entity>'
            '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
            '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
            '</xbrli:context></ix:resources></ix:header><ix:header><ix:resources><xbrli:unit id="u1">'
            '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
            '<p><ix:nonFraction id="fC" name="us-gaap:A" contextRef="c2" '
            'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction>'
            '<ix:nonFraction id="fD" name="us-gaap:B" contextRef="c2" '
            'unitRef="u1" scale="6" decimals="-6">726</ix:nonFraction></p>'
            '</body></html>')


def _member_event(axis=_GEO, member=_MEMBER, label="US", part=_PART,
                  *, store=None, extra_items=(), corrupt=None, **kw):
    """One event whose single item claims ONE real dimension."""
    from driver.core.driver_neo4j_adapter import GraphFactRows
    from driver.core.test_round10_event_boundary import _door_row

    doc = _dim_doc(axis, member)
    # THE SHARED five-key builder, so this file cannot drift from the graph
    # row shape the adapter really publishes. Named three keys before, which
    # made every event here park `XBRL_BINDING_UNAVAILABLE` on an incomplete
    # row and never reach the member-link law these tests are about.
    dims = [_ns_dim(axis, member, label)]

    class _DimStore(_Counting):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            self.row_reads.append(concept)
            fid = "fC" if concept.endswith("A") else "fD"
            return GraphFactRows(
                rows=[dict(_door_row(fid, concept=concept),
                           context_id="c2", dims=dims)],
                exclusions=())

    class _DimProvider:
        def __init__(self):
            self.fetches = 0

        def get_filing_document(self, source_id):
            self.fetches += 1
            return doc

    item = _door_item("us-gaap:A", "fC", doc=doc)
    item["member_refs"] = [{"axis": axis, "member": member,
                            "slice_part": part}]
    item["fact"]["item"]["slice_parts"] = [part]
    if corrupt:
        corrupt(item)
    items = [item, *extra_items]
    return attach_event_xbrl(items, source_id=_ACC,
                            store=store or _DimStore(),
                            filing_provider=_DimProvider(),
                            text_parts=parts_for(items),
                            menu_tokens=frozenset({part}), **kw)


def test_825p2_THE_FOLD_NOTE_SURVIVES_EXACTLY():
    """THE point of #825. `check_member_refs` produced this exact note and the
    door discarded it into `_notes`, so the evidence the live writer keeps
    would have been lost at the switch. Reproduced live: the fact attached (so
    the check ran) while `member_menu` came back empty."""
    res = _member_event()
    assert len(res.facts) == 1, "fixture must ATTACH, or the check never ran"
    assert dict(res.member_menu["folds"]) == {"0": (MappingProxyType(_NOTE),)}


def test_825p2_EMPTY_refs_invent_NO_fold_row():
    """The negative control: no refs, no fold row — never an empty placeholder
    that would read as 'checked and clean'."""
    assert dict(_two_item_event().member_menu["folds"]) == {}


@pytest.mark.parametrize("axis,member,event", [
    (_NON_SLICE, "geo:M", "non_slice_ref"),
    (_SEG, _ELIM, "fs20_hard_exclude"),
])
def test_825p2_MEMBER_failure_parks_MEMBER_LINK_INVALID_with_its_logs(
        axis, member, event):
    """Two things at once, both defects. The live writer parks
    MEMBER_LINK_INVALID; staged v2 raised a bare SchemaError, so the same
    breach became a CONTRACT REJECTION under a generic code — the channel
    would have been told to fix and resubmit something it cannot fix. And the
    structured exclusion log died with the exception."""
    res = _member_event(axis=axis, member=member, part="segment:x")
    assert len(res.facts) == 0
    row = res.preflight_outcomes[0]
    assert (row["decision"], row["codes"]) == ("parked", ("MEMBER_LINK_INVALID",))
    assert [dict(x) for x in res.member_menu["exclusions"]] == \
        [{"event": event, "axis": axis, "member": member,
          "where": "current_fact_ref"}]


def test_825p2_a_LATER_numeric_failure_does_not_erase_member_evidence():
    """The member check ran and produced a note; a numeric check AFTER it then
    parks the item. The note must still be in the result under that same
    original index — otherwise every audit trail ends at the first later
    failure."""
    from decimal import Decimal

    def wrong_value(item):
        item["fact"]["item"]["level_low"]["value"] = Decimal("999")

    res = _member_event(corrupt=wrong_value)
    assert len(res.facts) == 0, "the numeric law must still refuse this item"
    # WHICH word it gets is the numeric law's business, not this test's; what
    # #825 owns is that the evidence already produced is still here.
    assert res.preflight_outcomes[0]["index"] == 0
    assert dict(res.member_menu["folds"]) == {"0": (MappingProxyType(_NOTE),)}


def test_825p2_check_member_refs_runs_ONCE_PER_ITEM_not_once_per_event(
        monkeypatch):
    """One rule engine, one run PER APPLICABLE ITEM. With a single item this
    cannot tell once-per-item from once-per-event, so it uses TWO items sharing
    one concept — and pins that both attach, in input order, each keeping its
    own fold row."""
    import driver.core.slice_menu as sm
    calls = []
    real = sm.check_member_refs
    monkeypatch.setattr(sm, "check_member_refs",
                        lambda *a, **k: (calls.append(a), real(*a, **k))[1])
    second = _door_item("us-gaap:A", "fC", doc=_dim_doc())
    second["member_refs"] = [{"axis": _GEO, "member": _MEMBER,
                              "slice_part": _PART}]
    second["fact"]["item"]["slice_parts"] = [_PART]
    res = _member_event(extra_items=[second])
    assert [i for i, _f in res.facts] == [0, 1], "input order is output order"
    assert len(calls) == 2, "the member check must run per ITEM"
    assert sorted(res.member_menu["folds"]) == ["0", "1"]


def test_825p2_an_EMPTY_event_returns_the_SAME_RESULT_RECORD():
    """The door returned a bare `[]` here and an AttachResult everywhere else.
    One door, one return shape — a caller reading `.facts` crashed on the
    lawful no-XBRL event, which is EVERY 8-K."""
    res = attach_event_xbrl([], source_id=_ACC, store=_Counting(),
                            filing_provider=_CountingProvider(), text_parts=[])
    assert res.facts == () and res.preflight_outcomes == ()
    assert res.source_id == _ACC
    assert dict(res.member_menu) == {"folds": MappingProxyType({}),
                                     "exclusions": ()}


def test_825p2_ALL_INVALID_event_still_returns_the_result_record():
    """Nothing survived the pure phase: still the record, still zero I/O."""
    bad = _door_item("us-gaap:A", "fA")
    bad["fact"]["item"]["quote"] = "NOT IN THE FILING"
    store, provider = _Counting(), _CountingProvider()
    # The event view is supplied EXPLICITLY: `parts_for` derives each part's
    # content FROM the item's own quote, so it would make this item lawful and
    # the test would prove nothing.
    res = attach_event_xbrl([bad], source_id=_ACC, store=store,
                            filing_provider=provider,
                            text_parts=[{"part": "fA", "content": "unrelated"}])
    assert res.facts == () and len(res.preflight_outcomes) == 1
    assert (store.representation, store.cik, provider.fetches) == (0, 0, 0)

@pytest.mark.parametrize("bad", [
    {"nonsense": 1},                                   # unknown key
    {},                                                # no keys at all
    {1: "a", "concept": "c"},                          # MIXED-TYPE keys
    42, "text", ["a"], None, (), 5.0,                  # not a mapping at all
])
def test_825p2_a_MALFORMED_ITEM_is_ITEM_LOCAL_and_keeps_its_sibling(bad):
    """A malformed item inside a VALID envelope is that item's own rejection.
    The shape check ran in its own pass BEFORE the per-item loop, so one unknown
    key still erased every valid sibling — the exact contract defect #825 was
    opened to fix, surviving in the one place the fix had not reached.

    Mapping shapes and non-mapping types were two near-identical tests; they are
    one matrix, and it pins the exact row rather than just its index."""
    good = _door_item("us-gaap:A", "fA")
    res = attach_event_xbrl([good, bad], source_id=_ACC, store=_Counting(),
                            filing_provider=_CountingProvider(),
                            text_parts=parts_for([good]))
    assert [i for i, _f in res.facts] == [0], "the valid sibling was erased"
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (1, "rejected", ("XBRL_CONTRACT_INVALID",))


def test_825p2_an_UNIDENTIFIABLE_ENVELOPE_still_raises():
    """The other half of the same law: if the envelope cannot reliably index
    its items at all, there is no per-item outcome to report."""
    for envelope in ("not-a-list", {"a": 1}, (x for x in ()), 5):
        with pytest.raises(SchemaError):
            attach_event_xbrl(envelope, source_id=_ACC, store=_Counting(),
                              filing_provider=_CountingProvider(), text_parts=[])


def test_825p2_fact_id_stays_NONE_until_a_real_driver_fact_id_exists():
    """`part_ref` is the model's pointer into the event view, NOT a Driver fact
    id. Putting it in the `fact_id` field publishes a fabricated identity that
    joins to nothing, and it would look like a real id in the audit."""
    res = _member_event(axis=_SEG, member=_ELIM, part="segment:x")
    assert [o["fact_id"] for o in res.preflight_outcomes] == [None]


def test_825p2_a_POPULATED_result_is_deeply_frozen():
    """The old immutability test only ever saw an EMPTY result, so it could not
    notice that real audit data was handed out through a shallow copy."""
    res = _member_event()
    with pytest.raises(TypeError):
        res.member_menu["folds"]["0"] = ()
    note = res.member_menu["folds"]["0"][0]
    with pytest.raises(TypeError):
        note["fold"] = False
    assert isinstance(res.member_menu["folds"]["0"], tuple)


def test_825p2_a_POPULATED_exclusion_record_is_frozen_too():
    res = _member_event(axis=_SEG, member=_ELIM, part="segment:x")
    with pytest.raises(TypeError):
        res.member_menu["exclusions"][0]["event"] = "rewritten"


def test_825p2_the_public_decisions_are_EXACTLY_the_contract_five():
    """`values() <= PUBLIC_DECISIONS` was satisfiable by adding the retired
    decision STRING `parked_retry` to BOTH collections — it was never an
    exception class — which is precisely the drift being guarded against. Both
    sides are pinned exactly, against the words written in the contract."""
    from driver.core.prepared_fact_v2 import OUTCOME_CLASSES
    from driver.core.xbrl_attach import PUBLIC_DECISIONS
    # THE EXACT ORDERED TUPLE. A set comparison passed with `parked` appended
    # twice — verified by injection — so the duplicate the pin exists to catch
    # walked straight through it.
    assert PUBLIC_DECISIONS == ("written", "merged", "parked", "skipped",
                                "rejected")
    assert set(OUTCOME_CLASSES.values()) == {"rejected", "parked"}


def test_825p2_the_decision_rule_has_exactly_ONE_owner():
    """The code map must not restate a decision. Its keys must be EXACTLY the
    governed classes, so a class cannot exist in one map and not the other —
    the drift that having two owners makes possible."""
    from driver.core.prepared_fact_v2 import OUTCOME_CLASSES
    from driver.core.xbrl_attach import _DEFAULT_CODES, _default_outcome
    # LENGTH TOO. A duplicated governed class collapsed in the set comparison
    # and the one-owner test stayed green — verified by injection.
    assert len(_DEFAULT_CODES) == len(OUTCOME_CLASSES)
    assert {c for c, _ in _DEFAULT_CODES} == set(OUTCOME_CLASSES)
    for cls in OUTCOME_CLASSES:
        decision, _code = _default_outcome(cls("x"))
        assert decision == OUTCOME_CLASSES[cls], cls


def test_825p2_a_missing_graph_company_keeps_SOURCE_COMPANY_AMBIGUOUS():
    """The branch already OWNS a specific code — but it lived only inside the
    error MESSAGE, so the channel received the generic binding code and could
    not tell 'this filing has no single company' from any other park. The code
    is chosen by BRANCH here; nothing reads the message to decide."""
    class _NoCik(_Counting):
        def get_source_company_cik(self, source_id):
            self.cik += 1
            return ""

    item = _door_item("us-gaap:A", "fA")
    res = attach_event_xbrl([item], source_id=_ACC, store=_NoCik(),
                            filing_provider=_CountingProvider(),
                            text_parts=parts_for([item]))
    assert res.facts == ()
    row = res.preflight_outcomes[0]
    assert (row["decision"], row["codes"]) == ("parked",
                                              ("SOURCE_COMPANY_AMBIGUOUS",))


def test_825p2_an_UNSTORABLE_value_keeps_NOT_STORABLE_and_PARKS():
    """`SlotConversionError` was caught in the numeric loop and re-raised as
    `SchemaError`, so a value the store cannot materialise was reported to the
    channel as a CONTRACT VIOLATION to fix and resubmit. The filing is lawful;
    the value simply cannot be stored — that is NOT_STORABLE, and a park."""
    from decimal import Decimal

    from driver.core.driver_neo4j_adapter import GraphFactRows
    from driver.core.test_round10_event_boundary import _door_row

    # A LAWFUL filing at the EXACT scale that reaches the repaired branch.
    # Scale must be large enough that value x multiplier exceeds the 1024-char
    # stored form, yet small enough that the MULTIPLIER alone still fits: below
    # 1022 nothing fails, at 1024 `expected_multiplier` fails first and the
    # numeric loop is never entered. Verified empirically, not assumed — an
    # earlier version used 5000 and parked from `expected_multiplier`, so it
    # asserted the right outcome while never executing the line under repair.
    doc = (f'<html {_XMLNS}><body><ix:header><ix:resources><xbrli:context id="c1"><xbrli:entity>'
           '<xbrli:identifier scheme="http://www.sec.gov/CIK">0000320193</xbrli:identifier></xbrli:entity>'
           '<xbrli:period><xbrli:startDate>2024-01-01</xbrli:startDate>'
           '<xbrli:endDate>2024-06-30</xbrli:endDate></xbrli:period>'
           '</xbrli:context></ix:resources></ix:header><ix:header><ix:resources><xbrli:unit id="u1">'
           '<xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit></ix:resources></ix:header>'
           '<p><ix:nonFraction id="fA" name="us-gaap:A" contextRef="c1" '
           'unitRef="u1" scale="1022" decimals="-6">726</ix:nonFraction></p>'
           '</body></html>')

    class _BigStore(_Counting):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            self.row_reads.append(concept)
            return GraphFactRows(
                rows=[dict(_door_row("fA", concept=concept),
                           value=f"{726 * 10 ** 1022:,}")],
                exclusions=())

    class _BigProvider:
        def get_filing_document(self, source_id):
            return doc

    item = _door_item("us-gaap:A", "fA", doc=doc)
    for slot in ("level_low", "level_high"):
        item["fact"]["item"][slot]["scale_multiplier"] = Decimal(10) ** 1022
    res = attach_event_xbrl([item], source_id=_ACC, store=_BigStore(),
                            filing_provider=_BigProvider(),
                            text_parts=parts_for([item]))
    assert res.facts == ()
    row = res.preflight_outcomes[0]
    assert (row["decision"], row["codes"]) == ("parked", ("NOT_STORABLE",))


def test_825p2_a_STORE_OUTAGE_during_a_concept_read_fans_out_EVENT_WIDE():
    """An outage is not a property of the concept. Recording it as a
    concept-local absence would tell the channel that THIS concept is missing
    from the filing — a false and durable statement — while a sibling concept
    was reported clean from the same broken connection."""
    from driver.core.driver_neo4j_adapter import GraphFactRows
    from driver.core.test_round10_event_boundary import _door_row

    class _Flaky(_Counting):
        """ONE concept reads cleanly, the OTHER hits the outage. If every read
        failed, a concept-local implementation would park both items too and
        this test could not tell the two behaviours apart — which is exactly
        what it was doing before."""

        def get_xbrl_fact_dimensions(self, source_id, concept):
            self.row_reads.append(concept)
            if concept.endswith("B"):
                raise OSError("connection reset")
            return GraphFactRows(rows=[_door_row("fA", concept=concept)],
                                 exclusions=())

    good = _door_item("us-gaap:A", "fA")
    other = _door_item("us-gaap:B", "fB")
    items = [good, other]
    res = attach_event_xbrl(items, source_id=_ACC, store=_Flaky(),
                            filing_provider=_CountingProvider(),
                            text_parts=parts_for(items))
    assert res.facts == ()
    assert [o["index"] for o in res.preflight_outcomes] == [0, 1]
    assert {o["decision"] for o in res.preflight_outcomes} == {"parked"}
    assert {o["codes"] for o in res.preflight_outcomes} == \
        {("SOURCE_UNAVAILABLE",)}


def test_825p2_an_ORDINARY_concept_absence_stays_CONCEPT_LOCAL():
    """The other side of the same rule, so the fix above cannot be a blanket
    fan-out: a concept the filing genuinely does not carry parks only the items
    claiming it."""
    from driver.core.driver_neo4j_adapter import GraphFactRows
    from driver.core.test_round10_event_boundary import _door_row

    class _OnlyA(_Counting):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            self.row_reads.append(concept)
            if concept.endswith("B"):
                return GraphFactRows(rows=[], exclusions=())
            return GraphFactRows(rows=[_door_row("fA", concept=concept)],
                                 exclusions=())

    items = [_door_item("us-gaap:A", "fA"), _door_item("us-gaap:B", "fB")]
    res = attach_event_xbrl(items, source_id=_ACC, store=_OnlyA(),
                            filing_provider=_CountingProvider(),
                            text_parts=parts_for(items))
    assert [i for i, _f in res.facts] == [0], "the sibling concept was erased"
    row = res.preflight_outcomes[0]
    assert (row["index"], row["decision"], row["codes"]) == \
        (1, "parked", ("XBRL_BINDING_UNAVAILABLE",))


def test_825p2_a_REPEATED_concept_reads_ONCE_and_logs_its_exclusions_ONCE():
    """The event-local cache is what makes the exclusion count honest: reading
    twice would double-count the same silent drop."""
    from driver.core.driver_neo4j_adapter import GraphFactRows
    from driver.core.test_round10_event_boundary import _door_row

    rec = {"event": "dimension_member_array_misaligned",
           "where": "graph_fact_dimensions", "concept": "us-gaap:A",
           "fact_count": 3, "context_count": 2}

    class _Excluding(_Counting):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            self.row_reads.append(concept)
            return GraphFactRows(rows=[_door_row("fA", concept=concept)],
                                 exclusions=(MappingProxyType(dict(rec)),))

    store = _Excluding()
    items = [_door_item("us-gaap:A", "fA"), _door_item("us-gaap:A", "fA")]
    res = attach_event_xbrl(items, source_id=_ACC, store=store,
                            filing_provider=_CountingProvider(),
                            text_parts=parts_for(items))
    assert store.row_reads == ["us-gaap:A"], "the concept was read twice"
    assert [dict(x) for x in res.member_menu["exclusions"]] == [rec]


def test_825p2_the_result_survives_CALLER_MUTATION_of_the_notes_it_came_from():
    """The audit records must be COPIES. A note handed straight out of
    `check_member_refs` is still the list that function built."""
    import driver.core.slice_menu as sm
    escaped = []
    real = sm.check_member_refs

    def capture(*a, **k):
        problems, notes, logs = real(*a, **k)
        escaped.append((notes, logs))
        return problems, notes, logs

    import pytest as _p
    mp = _p.MonkeyPatch()
    mp.setattr(sm, "check_member_refs", capture)
    try:
        res = _member_event()
    finally:
        mp.undo()
    notes, logs = escaped[0]
    notes.append({"slice_part": "INJECTED"})
    notes[0]["fold"] = "INJECTED" if notes[0] is not None else None
    logs.append({"event": "INJECTED"})
    assert dict(res.member_menu["folds"]) == {"0": (MappingProxyType(_NOTE),)}
    assert res.member_menu["exclusions"] == ()


def test_825p2_the_audit_SERIALIZER_reproduces_the_v1_member_menu_exactly():
    """The switch copies `member_menu` into the existing write-ahead audit. The
    ONE serializer must render immutable mappings as the same JSON the live v1
    writer produces — not as `str(mappingproxy(...))`."""
    import json

    from driver.core.driver_write_cli import _jsonable
    res = _member_event()
    text = json.dumps({"member_menu": res.member_menu}, default=_jsonable)
    assert json.loads(text) == {
        "member_menu": {"folds": {"0": [_NOTE]}, "exclusions": []}}


# --------------------------------------------------------------------------
# #827 finding 4 — the typed/misaligned exclusions are ADAPTER-OWNED and are
# consumed ONCE. Reconciled from the live code BEFORE any change was
# considered: v1 (`driver_write_cli`) extends its audit log from
# `read.exclusions` once per concept, and v2 (`xbrl_attach`) carries the same
# adapter namedtuple field — neither recomputes, re-derives or drops them. The
# ruling was "if v1 already consumes them exactly once, change nothing", so
# NOTHING was changed. This test is the evidence, and it fails the day either
# side starts recomputing, doubling or dropping the adapter's own audit.
# --------------------------------------------------------------------------

def test_827_adapter_exclusions_are_CARRIED_once_never_recomputed():
    """The adapter is the ONE counter. For a concept read once, the door must
    surface exactly what the adapter reported — same content, same
    multiplicity — even though TWO items share that concept.

    The graph fixture SUBCLASSES the lawful owner (`_Counting`) so the items
    really bind: an earlier refusal would prove nothing about this gate, and
    the first version of this test failed exactly that way.
    """
    from driver.core.driver_neo4j_adapter import GraphFactRows
    from driver.core.test_round10_event_boundary import (_Counting,
                                                         _CountingProvider,
                                                         _door_item, parts_for)
    from driver.core.xbrl_attach import attach_event_xbrl

    dropped = ({"reason": "typed dimension", "fact_id": "f1"},
               {"reason": "misaligned context", "fact_id": "f2"})

    class _ExcludingGraph(_Counting):
        def get_xbrl_fact_dimensions(self, source_id, concept):
            read = super().get_xbrl_fact_dimensions(source_id, concept)
            return GraphFactRows(rows=read.rows, exclusions=dropped)

    store = _ExcludingGraph()
    items = [_door_item("us-gaap:A", "fA"), _door_item("us-gaap:A", "fA")]
    res = attach_event_xbrl(items, source_id="0000006201-26-000031",
                            store=store, filing_provider=_CountingProvider(),
                            text_parts=parts_for(items))

    # THE GATE IS REACHED: both items bound, nothing was refused earlier.
    assert res.preflight_outcomes == (), [dict(o) for o in res.preflight_outcomes]
    assert len(res.facts) == 2, res.facts
    # ONE read for the shared concept — so the exclusions are carried once,
    # not once per item.
    assert store.row_reads == ["us-gaap:A"], store.row_reads
    audit = [dict(x) for x in res.member_menu["exclusions"]]
    assert audit == [dict(d) for d in dropped], (
        f"the door did not carry the adapter's exclusions verbatim: {audit}")
