"""slice_menu.py law tests: the frozen table, the catalog §6 3-way ladder, FS-20
elimination handling, PIT menu construction, and every ref-level park shape
(each parks MEMBER_LINK_INVALID through the real CLI)."""
from driver.core.driver_ids import encode_unknown_axis
from driver.core.slice_menu import (CONFIRMED_AXES, ELIMINATION_QNAMES,
                                    NON_SLICE_AXES, build_menu, check_member_refs,
                                    classify_axis, match_xbrl_fact,
                                    slice_tokens_from_scope)
from driver.core.test_driver_write_cli import FakeStore, audit_docs, fact, run

GEO = "srt:StatementGeographicalAxis"
SEG = "us-gaap:StatementBusinessSegmentsAxis"
ELIM = "us-gaap:IntersegmentEliminationMember"


def test_frozen_table_shape_and_ladder():
    assert len(CONFIRMED_AXES) == 57               # catalog §2, transcribed whole
    assert set(CONFIRMED_AXES.values()) == {
        "segment", "product", "geography", "customer", "channel",
        "entity_ownership"}                        # ID-law kinds, 6 exactly
    assert len(NON_SLICE_AXES) == 7                # ONLY the proven §3 name-liars
    assert not (NON_SLICE_AXES & set(CONFIRMED_AXES))
    assert classify_axis(GEO) == ("slice", "geography")
    assert classify_axis("eqt:DistributionChannelAxis") == ("non_slice", None)
    assert classify_axis("acme:MysteryAxis") == ("unknown", None)
    # the live lesson: a REAL slice axis nobody catalogued (246 Agilent
    # end-market facts) must take the safe unknown/provisional path — the
    # census complement that called it non-slice is DELETED
    assert classify_axis("a:EndMarketsAxis") == ("unknown", None)


def test_scope_slice_token_parse():
    assert slice_tokens_from_scope(
        "period=gp_2025-01-01_2025-03-31|slice=geography:us;segment:eu"
        "|measurement=adjusted|quote_hash=abc") == {"geography:us", "segment:eu"}
    assert slice_tokens_from_scope("period=gp_2025-01-01_2025-03-31") == set()
    assert slice_tokens_from_scope("") == set()


def test_build_menu_classifies_excludes_and_logs():
    tokens, logs = build_menu(
        xbrl_members=[
            {"axis": GEO, "member": "country:US", "label": "UNITED STATES"},
            {"axis": SEG, "member": ELIM, "label": "Intersegment Eliminations"},
            {"axis": "eqt:DistributionChannelAxis", "member": "x:WTI",
             "label": "West Texas"},                        # non-slice: skipped
            {"axis": "acme:MysteryAxis", "member": "acme:ThingMember",
             "label": "Thing"},                             # unknown: sentinel enters
            {"axis": GEO, "member": "country:XX", "label": "—"}],  # unusable label
        used_scopes=["period=gp_2025-01-01_2025-03-31|slice=segment:consumer"])
    assert tokens == frozenset({
        "geography:united_states",
        encode_unknown_axis("acme:MysteryAxis", "Thing"),
        "segment:consumer"})
    assert [(l["event"], l.get("member")) for l in logs] == [
        ("fs20_hard_exclude", ELIM),               # dropped AND logged (FS-20)
        ("menu_label_unusable", "country:XX")]


def _refs_fact(refs, slice_parts):
    return fact(slice_parts=slice_parts, member_refs=refs,
                xbrl_concept_raw="us-gaap:Revenues")


def _verify_store(dims, **kw):
    # the current filing carries a fact with EXACTLY these dims for the default
    # fact() claim period (stored end exclusive)
    return FakeStore(xbrl_facts={"us-gaap:Revenues": [
        {"period_type": "duration", "start_date": "2025-06-29",
         "end_date": "2025-09-28", "dims": [dict(d) for d in dims]}]}, **kw)


def test_check_member_refs_unit_park_shapes():
    toks = {"geography:us"}
    matched = [{"axis": GEO, "member": "m", "label": "US"},
               {"axis": "acme:MysteryAxis", "member": "m", "label": "US"}]
    bad = [
        ({"axis": "eqt:DistributionChannelAxis", "member": "m",
          "slice_part": "channel:x"}, "NON-slice"),
        ({"axis": SEG, "member": ELIM, "slice_part": "segment:x"},
         "pure elimination"),
        ({"axis": GEO, "member": "ghost", "slice_part": "geography:us"},
         "not a dimension of the matched fact"),
        ({"axis": GEO, "member": "m", "slice_part": "segment:us"},
         "not derivable"),                         # label recompute beats claims
        ({"axis": "acme:MysteryAxis", "member": "m",
          "slice_part": "geography:us"}, "not derivable"),  # sentinel expected
        ({"axis": GEO, "member": "m", "slice_part": "geography:europe"},
         "not derivable"),                         # label says us, claim says europe
    ]
    for ref, needle in bad:
        problems, notes, _ = check_member_refs([ref], toks, frozenset(), matched)
        assert notes == [] and len(problems) == 1 and needle in problems[0]
    ok, notes, logs = check_member_refs(
        [{"axis": GEO, "member": "m", "slice_part": "geography:us"}],
        toks, frozenset({"geography:us"}), matched)
    assert ok == [] and notes[0]["fold"] is True and logs == []
    # the current-fact exclusion is LOGGED, structured (item-4 requirement)
    problems, _, logs = check_member_refs(
        [{"axis": SEG, "member": ELIM, "slice_part": "segment:x"}],
        toks, frozenset(), matched)
    assert logs == [{"event": "fs20_hard_exclude", "axis": SEG, "member": ELIM,
                     "where": "current_fact_ref"}]
    # verified but supporting none of the fact's own tokens still parks
    problems, _, _ = check_member_refs(
        [{"axis": GEO, "member": "m", "slice_part": "geography:us"}],
        {"segment:eu"}, frozenset(), matched)
    assert "supports no slice token" in problems[0]


def test_match_xbrl_fact_exclusive_end_decode():
    # stored XBRL ends are EXCLUSIVE (verified ruling): claimed inclusive
    # 2025-06-29..2025-09-27 matches stored 2025-06-29..2025-09-28; an instant
    # stores its date in start_date as claimed+1
    dur = {"period_type": "duration", "start_date": "2025-06-29",
           "end_date": "2025-09-28", "dims": []}
    ins = {"period_type": "instant", "start_date": "2025-09-28",
           "end_date": "null", "dims": []}
    claim = {"time_type": "duration", "start": "2025-06-29",
             "end": "2025-09-27", "dims": set()}
    assert match_xbrl_fact(claim, [dur]) == []
    assert match_xbrl_fact(dict(claim, end="2025-09-28"), [dur]) is None
    iclaim = {"time_type": "instant", "start": None, "end": "2025-09-27",
              "dims": set()}
    assert match_xbrl_fact(iclaim, [ins]) == []
    assert match_xbrl_fact(dict(iclaim, end="2025-09-28"), [ins]) is None


def test_match_xbrl_fact_complete_dimension_set_only():
    row = {"period_type": "duration", "start_date": "2025-06-29",
           "end_date": "2025-09-28",
           "dims": [{"axis": GEO, "member": "a", "label": "A"},
                    {"axis": SEG, "member": "b", "label": "B"}]}
    base = {"time_type": "duration", "start": "2025-06-29", "end": "2025-09-27"}
    assert match_xbrl_fact(dict(base, dims={(GEO, "a"), (SEG, "b")}),
                           [row]) == row["dims"]
    assert match_xbrl_fact(dict(base, dims={(GEO, "a")}), [row]) is None  # subset
    assert match_xbrl_fact(dict(base, dims=set()), [row]) is None  # false []


def test_e2e_elimination_member_ref_parks_with_exclusion_logged(tmp_path):
    store = _verify_store([{"axis": SEG, "member": ELIM,
                            "label": "Intersegment Eliminations"}])
    out = run(tmp_path, [_refs_fact(
        [{"axis": SEG, "member": ELIM, "slice_part": "segment:eliminations"}],
        slice_parts=[("segment", "Eliminations")])], store)
    item = out["items"][0]
    assert item["decision"] == "parked" and item["codes"] == ["MEMBER_LINK_INVALID"]
    assert "pure elimination" in item["detail"]
    # ... and the current-fact exclusion lands STRUCTURED in the audit
    doc = audit_docs(tmp_path)[0]
    assert {"event": "fs20_hard_exclude", "axis": SEG, "member": ELIM,
            "where": "current_fact_ref"} in doc["member_menu"]["exclusions"]


def test_e2e_non_slice_axis_ref_parks(tmp_path):
    store = _verify_store([{"axis": "eqt:DistributionChannelAxis",
                            "member": "x:WTI", "label": "West Texas"}])
    out = run(tmp_path, [_refs_fact(
        [{"axis": "eqt:DistributionChannelAxis", "member": "x:WTI",
          "slice_part": "channel:wti"}], slice_parts=[("channel", "WTI")])], store)
    assert out["items"][0]["codes"] == ["MEMBER_LINK_INVALID"]
    assert "NON-slice" in out["items"][0]["detail"]


def test_e2e_uncatalogued_real_axis_writes_via_provisional_path(tmp_path):
    # THE a:EndMarketsAxis case (246 real Agilent end-market facts): an axis
    # the catalog never reviewed takes the unknown->provisional sentinel path
    # and the fact WRITES — never silently discarded (FINAL_DESIGN:171)
    part = encode_unknown_axis("a:EndMarketsAxis", "Food Market")
    store = _verify_store([{"axis": "a:EndMarketsAxis",
                            "member": "a:FoodMarketMember",
                            "label": "Food Market"}])
    out = run(tmp_path, [_refs_fact(
        [{"axis": "a:EndMarketsAxis", "member": "a:FoodMarketMember",
          "slice_part": part}],
        slice_parts=[("unknown", part.split(":", 1)[1])])], store)
    assert out["items"][0]["decision"] == "written"


def test_e2e_kind_mismatch_ref_parks(tmp_path):
    # supplied slice_part claims segment; the filing's own label recomputes to
    # geography:us — the claim is never trusted, the fact parks
    store = _verify_store([{"axis": GEO, "member": "country:US", "label": "US"}])
    out = run(tmp_path, [_refs_fact(
        [{"axis": GEO, "member": "country:US", "slice_part": "segment:us"}],
        slice_parts=[("segment", "US")])], store)
    assert out["items"][0]["codes"] == ["MEMBER_LINK_INVALID"]
    assert "not derivable" in out["items"][0]["detail"]


def test_e2e_menu_arm_a_xbrl_members_feed_the_fold(tmp_path):
    # the SAME company member seen in a PRIOR 10-K folds the incoming ref;
    # the current filing's own row only VERIFIES, never self-folds
    store = _verify_store([{"axis": GEO, "member": "country:XX",
                            "label": "International"}],
                          slice_menu={"xbrl_members": [
                              {"axis": GEO, "member": "country:XX",
                               "label": "International"}], "used_scopes": []})
    out = run(tmp_path, [_refs_fact(
        [{"axis": GEO, "member": "country:XX",
          "slice_part": "geography:international"}],
        slice_parts=[("geography", "International")])], store)
    assert out["items"][0]["decision"] == "written"
    doc = audit_docs(tmp_path)[0]
    assert doc["member_menu"]["folds"]["0"][0]["fold"] is True
    assert doc["member_menu"]["exclusions"] == []


def test_provisional_member_enters_menu_with_structured_log():
    # a censused provisional member (own row, read-layer quarantine): it still
    # ENTERS the write-side menu, with a structured log
    tokens, logs = build_menu(
        xbrl_members=[{"axis": SEG, "member": "awi:UnallocatedCorporateMember",
                       "label": "Unallocated Corporate"}], used_scopes=[])
    assert "segment:unallocated_corporate" in tokens
    assert logs == [{"event": "fs20_provisional", "axis": SEG,
                     "member": "awi:UnallocatedCorporateMember",
                     "token": "segment:unallocated_corporate"}]


def test_elimination_qname_outside_segment_family_is_not_guarded():
    # FS-20 scopes hard-exclusion to SEGMENT-FAMILY axes only — the same qname
    # on a geography axis is not this guard's business (parks later only if
    # unverifiable); build_menu keeps it as an ordinary member
    tokens, logs = build_menu(
        xbrl_members=[{"axis": GEO, "member": ELIM, "label": "Somewhere"}],
        used_scopes=[])
    assert tokens == frozenset({"geography:somewhere"}) and logs == []


def test_frozen_census_lists_load_and_stay_disjoint():
    from driver.core.slice_axis_frozen import (HARD_EXCLUDE_ELIMINATIONS,
                                               PROVISIONAL_MEMBERS)
    assert len(HARD_EXCLUDE_ELIMINATIONS) == 12    # hand-vetted, exact qnames
    assert len(PROVISIONAL_MEMBERS) == 79
    assert not (HARD_EXCLUDE_ELIMINATIONS & PROVISIONAL_MEMBERS)
    assert "ecl:GlobalPestEliminationMember" not in HARD_EXCLUDE_ELIMINATIONS
    assert "pbf:PriortoeliminationMember" not in HARD_EXCLUDE_ELIMINATIONS
    # there is NO axis complement anymore — unreviewed axes go provisional
    import driver.core.slice_axis_frozen as frozen_mod
    assert not hasattr(frozen_mod, "NON_SLICE_CENSUS")
