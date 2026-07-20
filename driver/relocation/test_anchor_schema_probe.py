"""Anchor schema probe — durable, zero-write, zero-token (Universal Locator v5.5 §2).

Proves: the id/fact_scope grammar + stored fields + edges carry EVERY anchor component, with a
STRICT metric-only decoder that (a) rejects `surprise=` and unknown slots, (b) asserts
Driver-name/type agreement, (c) asserts stored fact_scope == id suffix, and (d) resolves the
company ONLY from the source id PARSED OUT OF THE FACT ID via an edge map. The edge map is TRUSTED
internal output of the exactly-one graph-edge query: the probe proves parsed-source lookup and
rejects missing/cross-wired KEYS — it does not authenticate a fabricated VALUE under the correct
key (duplicating graph validation here would be pointless).

Scope, stated exactly: ids are composed by Core's AUTHORITATIVE pure id law
(`driver/core/driver_ids.py`, test-only import) and the decoder under test is independent.
ONLY the source→Company edges are loaded LIVE (exactly one per pinned accession, else FAIL);
quote/unit/Driver payloads are PINNED FIXTURES. Fixtures use legal period forms, but this probe
does NOT validate period legality — Core's validators own that and nothing here duplicates them.
ZERO fiscal.ai/channel imports (Neo4j env read neutrally from the repo .env).

    venv/bin/python -m pytest driver/relocation/test_anchor_schema_probe.py -q

Skip policy: ONLY a genuinely unavailable graph skips; query errors or missing pinned edges FAIL.
NOT proven here (mandatory S4/WP2 gate): reconstruction from live graph nodes, birth_quotes
persistence on real nodes, locator accuracy from rebuilt anchors.
"""
import os
import sys
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
sys.path.insert(0, os.path.join(_REPO, "driver", "core"))   # test-only: the authoritative id law
import driver_ids as DI                                      # pure functions, no I/O


# ---------- neutral Neo4j env (no channel imports) ----------
def _neo4j_env():
    env = {}
    with open(os.path.join(_REPO, ".env")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.removeprefix("export ").strip()] = v.strip().strip("'\"")
    return env


def _one_company_edge(session, accession):
    """The source→Company edge for one accession — must be EXACTLY one, else FAIL (never skip)."""
    rows = list(session.run(
        """MATCH (r:Report {accessionNo:$a})-[:PRIMARY_FILER]->(c:Company)
           RETURN c.cik AS cik""", a=accession))
    assert len(rows) == 1, f"expected exactly one company edge for {accession}, got {len(rows)}"
    return rows[0]["cik"]


def _graph_session():
    """Connect or skip — ONLY on genuine unavailability. Query errors later still fail."""
    env = _neo4j_env()
    try:
        from neo4j import GraphDatabase
        from neo4j.exceptions import ServiceUnavailable
    except ImportError:
        pytest.skip("neo4j driver not installed")
    try:
        g = GraphDatabase.driver(env["NEO4J_URI"],
                                 auth=(env.get("NEO4J_USERNAME", "neo4j"), env["NEO4J_PASSWORD"]))
        g.verify_connectivity()
        return g
    except (ServiceUnavailable, OSError, KeyError) as e:
        pytest.skip(f"live graph genuinely unavailable: {e}")


# ---------- THE strict metric-only decoder under test (independent of core) ----------
ALLOWED_SLOTS = ("period", "slice", "measurement", "quote_hash")   # surprise= NOT allowed


def strict_decode(fact_id, props, driver_node, edge_map):
    """edge_map: {source_id: company_key} — the ONLY way a company enters. The decoder looks up
    the source id PARSED FROM THE FACT ID; a fact whose own source is not in the map FAILS.
    (The decoder is as right as the resolver; in real tests the resolver is a live
    exactly-one-edge graph query keyed by the same accession.)"""
    seg = fact_id.split(":", 3)
    assert len(seg) == 4 and seg[0] == "du", f"bad id shape: {fact_id!r}"
    _, source_id, driver, scope = seg
    if props["fact_scope"] != scope:
        raise ValueError(f"stored fact_scope != id suffix: {props['fact_scope']!r} vs {scope!r}")
    parsed = {}
    for slot in scope.split("|"):
        k, _, v = slot.partition("=")
        if k not in ALLOWED_SLOTS:
            raise ValueError(f"metric-only decoder: forbidden/unknown slot {k!r}")
        if k in parsed:
            raise ValueError(f"duplicate slot {k!r}")
        parsed[k] = v
    assert "period" in parsed, "period slot missing"
    if driver_node["name"] != driver:
        raise ValueError(f"Driver node name {driver_node['name']!r} != id driver {driver!r}")
    if driver_node["fact_type"] != "metric":
        raise ValueError(f"not a metric Driver: {driver_node['fact_type']!r}")
    company = edge_map.get(source_id)
    if company is None:
        raise ValueError(f"no company edge for THIS fact's source id {source_id!r} "
                         f"(cross-wired or missing edge)")
    anchor = {
        "source_id": source_id,
        "company": company,
        "driver": driver,
        "slice": parsed.get("slice", ""),
        "measurement": parsed.get("measurement", ""),
        "series_unit": props["series_unit"],
        "time_type": props["time_type"],
        "fact_type": driver_node["fact_type"],
        "wording": tuple(driver_node["definitional_evidence"]["birth_quotes"]),
    }
    return anchor, sorted(k for k in ("period", "quote_hash") if k in parsed)


def drv(name, bq):
    return {"name": name, "fact_type": "metric",
            "definitional_evidence": {"birth_quotes": list(bq)}}


def props(fid, series_unit, time_type, quote=None, **slots):
    """simulated stored node props: fact_scope mirrors the writer (= the id suffix). Value
    slots mirror Core's _NUMERIC_SIG names; a unit-carrying fixture stores level_low=0 —
    ZERO counts as numeric (is-not-None law) — a unitless fixture stores all-None
    (numberless). Override any slot via kwargs."""
    p = {"fact_scope": fid.split(":", 3)[3], "series_unit": series_unit, "time_type": time_type,
         "level_low": 0 if series_unit is not None else None, "level_high": None,
         "change_value": None, "comparison_low": None, "comparison_high": None}
    if quote is not None:
        p["quote"] = quote
    p.update(slots)
    return p


# ---------- pinned accessions (from part1 harvest data); edges loaded LIVE in their tests ----------
AA_ACC = "0000950170-25-024242"    # Alcoa 10-K
AAL_ACC = "0000006201-25-000010"   # American Airlines


def test_1_real_edge_aa_numeric_text():
    fid, _ = DI.build_id(AA_ACC, "revenue", period_id="gp_2024-01-01_2024-12-31",
                         slice_parts=(("geography", "United States"),))
    assert fid == ("du:0000950170-25-024242:revenue:"
                   "period=gp_2024-01-01_2024-12-31|slice=geography:united_states")
    g = _graph_session()
    with g.session() as s:
        edge_map = {AA_ACC: _one_company_edge(s, AA_ACC)}
    g.close()
    a, stripped = strict_decode(fid, props(fid, "m_usd", "duration"),
                                drv("revenue", ("United States (1) $ 5,365",)), edge_map)
    assert a["slice"] == "geography:united_states" and a["company"] == edge_map[AA_ACC]
    assert stripped == ["period"]


def test_2_synthetic_dimensionless():
    fid, _ = DI.build_id("SYN-ACC-A", "revenue", period_id="gp_2023-10-01_2024-09-28")
    a, stripped = strict_decode(fid, props(fid, "m_usd", "duration"),
                                drv("revenue", ("Total revenue $ 6,707",)), {"SYN-ACC-A": "SYNCIK-A"})
    assert a["slice"] == "" and a["measurement"] == "" and stripped == ["period"]


def test_3_synthetic_dimensioned_segment_normalized():
    fid, _ = DI.build_id("SYN-ACC-B", "revenue", period_id="gp_2024-11-01_2025-01-31",
                         slice_parts=(("segment", "Life Sciences & Applied Markets"),))
    a, _ = strict_decode(fid, props(fid, "m_usd", "duration"),
                         drv("revenue", ("Life sciences and applied markets $ 968",)),
                         {"SYN-ACC-B": "SYNCIK-B"})
    assert a["slice"].startswith("segment:life_sciences")


def test_4_synthetic_numberless_duration_series_unit_none():
    fid, _ = DI.build_id("SYN-ACC-C", "weather_condition", period_id="gp_2024-01-01_2024-03-31")
    a, _ = strict_decode(fid, props(fid, None, "duration"),
                         drv("weather_condition", ("unusually cold winter across texas",)),
                         {"SYN-ACC-C": "SYNCIK-C"})
    assert a["series_unit"] is None and a["time_type"] == "duration"
    assert a["wording"] == ("unusually cold winter across texas",)


def test_5_synthetic_instant_uses_legal_gp_date_date():
    fid, _ = DI.build_id("SYN-ACC-D", "store_count", period_id="gp_2025-12-31_2025-12-31")
    a, _ = strict_decode(fid, props(fid, "count", "instant"),
                         drv("store_count", ("International Stores 86 at fiscal year end",)),
                         {"SYN-ACC-D": "SYNCIK-D"})
    assert a["time_type"] == "instant"


def test_6_synthetic_collision_member_hash_stripped():
    qh = DI.signature_hash([None] * 8 + ["a", None])
    bare, _ = DI.build_id("SYN-ACC-E", "inventory_writedown", period_id="gp_2024-01-01_2024-03-31")
    member = DI.member_id(bare, qh)
    d = drv("inventory_writedown", ("inventory write-down of $ 12",))
    em = {"SYN-ACC-E": "SYNCIK-E"}
    a1, s1 = strict_decode(bare, props(bare, "m_usd", "duration"), d, em)
    a2, s2 = strict_decode(member, props(member, "m_usd", "duration"), d, em)
    assert a1 == a2 and s1 == ["period"] and s2 == ["period", "quote_hash"]


def test_7_synthetic_two_series_one_driver():
    d = drv("operating_margin", ("operating margin was 12.4%",))
    em = {"SYN-ACC-F": "SYNCIK-F"}
    f1, _ = DI.build_id("SYN-ACC-F", "operating_margin", period_id="gp_2024-01-01_2024-12-31")
    f2, _ = DI.build_id("SYN-ACC-F", "operating_margin", period_id="gp_2024-01-01_2024-12-31",
                        measurement_tokens=("adjusted",))
    a, _ = strict_decode(f1, props(f1, "percent", "duration"), d, em)
    b, _ = strict_decode(f2, props(f2, "percent", "duration"), d, em)
    assert a != b and b["measurement"] == "adjusted"


def test_8_synthetic_replaced_lww_quote_uses_birth_quotes():
    d = drv("store_count", ("International Stores 86 at fiscal year end",))
    fid, _ = DI.build_id("SYN-ACC-G", "store_count", period_id="gp_2025-12-31_2025-12-31")
    a, _ = strict_decode(fid, props(fid, "count", "instant"), d, {"SYN-ACC-G": "SYNCIK-G"})
    assert a["wording"] == ("International Stores 86 at fiscal year end",)


def test_9_metric_decoder_rejects_surprise_and_unknown_slots():
    fid, _ = DI.build_id("SYN-ACC-H", "eps", period_id="gp_2024-01-01_2024-03-31",
                         surprise="actual_vs_consensus")
    with pytest.raises(ValueError, match="forbidden/unknown"):
        strict_decode(fid, props(fid, "usd", "duration"), drv("eps", ("EPS of $ 1.23",)),
                      {"SYN-ACC-H": "C"})
    plain, _ = DI.build_id("SYN-ACC-H", "eps", period_id="gp_2024-01-01_2024-03-31")
    bogus = plain + "|bogus=1"
    with pytest.raises(ValueError, match="forbidden/unknown"):
        strict_decode(bogus, {"fact_scope": bogus.split(":", 3)[3],
                              "series_unit": "usd", "time_type": "duration"},
                      drv("eps", ("EPS of $ 1.23",)), {"SYN-ACC-H": "C"})


def test_10_driver_name_mismatch_rejected():
    fid, _ = DI.build_id("SYN-ACC-I", "revenue", period_id="gp_2024-01-01_2024-12-31")
    with pytest.raises(ValueError, match="!= id driver"):
        strict_decode(fid, props(fid, "m_usd", "duration"), drv("gross_margin", ("q",)),
                      {"SYN-ACC-I": "C"})


def test_11_stored_fact_scope_must_match_id_suffix():
    fid, _ = DI.build_id("SYN-ACC-J", "revenue", period_id="gp_2024-01-01_2024-12-31")
    bad = props(fid, "m_usd", "duration")
    bad["fact_scope"] = "period=gp_2020-01-01_2020-12-31"
    with pytest.raises(ValueError, match="stored fact_scope != id suffix"):
        strict_decode(fid, bad, drv("revenue", ("q",)), {"SYN-ACC-J": "C"})


def test_12_cross_wired_company_rejected():
    """The round-9 defect, pinned: a company supplied for a DIFFERENT source must never bind.
    The decoder may only use the edge of the fact's OWN parsed source id."""
    fid, _ = DI.build_id(AA_ACC, "revenue", period_id="gp_2024-01-01_2024-12-31")
    wrong_map = {AAL_ACC: "0000006201"}          # an edge — but for ANOTHER source
    with pytest.raises(ValueError, match="cross-wired or missing edge"):
        strict_decode(fid, props(fid, "m_usd", "duration"), drv("revenue", ("q",)), wrong_map)
    with pytest.raises(ValueError, match="cross-wired or missing edge"):
        strict_decode(fid, props(fid, "m_usd", "duration"), drv("revenue", ("q",)), {})


def test_13_real_cross_company_isolation_two_live_edges():
    """Same driver name, two REAL companies — edges loaded live, exactly one each, keyed by
    each fact's own accession."""
    g = _graph_session()
    with g.session() as s:
        edge_map = {AA_ACC: _one_company_edge(s, AA_ACC),
                    AAL_ACC: _one_company_edge(s, AAL_ACC)}
    g.close()
    assert edge_map[AA_ACC] != edge_map[AAL_ACC], "pinned accessions must be distinct companies"
    d = drv("revenue", ("q",))
    f1, _ = DI.build_id(AA_ACC, "revenue", period_id="gp_2024-01-01_2024-12-31")
    f2, _ = DI.build_id(AAL_ACC, "revenue", period_id="gp_2024-01-01_2024-12-31")
    x, _ = strict_decode(f1, props(f1, "m_usd", "duration"), d, edge_map)
    y, _ = strict_decode(f2, props(f2, "m_usd", "duration"), d, edge_map)
    assert x != y and x["company"] != y["company"]


# ---------- WP2 step 1 (plan v4): reconstruction tests call the PRODUCTION rebuild_anchor ----------
sys.path.insert(0, _HERE)
from locator import rebuild_anchor                       # the REAL neutral entrypoint, not a test double


def test_14_production_parity_with_strict_decode_on_green_fixtures():
    """The production function reconstructs EVERY strict-decode field exactly (it may ADD clue
    fields); parity across the synthetic fixture shapes: dimensionless, dimensioned, numberless,
    instant, measurement series."""
    cases = [
        ("SYN-ACC-A", "revenue", dict(period_id="gp_2023-10-01_2024-09-28"),
         "m_usd", "duration", ("Total revenue $ 6,707",)),
        ("SYN-ACC-B", "revenue", dict(period_id="gp_2024-11-01_2025-01-31",
                                      slice_parts=(("segment", "Life Sciences & Applied Markets"),)),
         "m_usd", "duration", ("Life sciences and applied markets $ 968",)),
        ("SYN-ACC-C", "weather_condition", dict(period_id="gp_2024-01-01_2024-03-31"),
         None, "duration", ("unusually cold winter across texas",)),
        ("SYN-ACC-D", "store_count", dict(period_id="gp_2025-12-31_2025-12-31"),
         "count", "instant", ("International Stores 86 at fiscal year end",)),
        ("SYN-ACC-F", "operating_margin", dict(period_id="gp_2024-01-01_2024-12-31",
                                               measurement_tokens=("adjusted",)),
         "percent", "duration", ("operating margin was 12.4%",)),
    ]
    for acc, name, kw, unit, tt, bq in cases:
        fid, _ = DI.build_id(acc, name, **kw)
        em = {acc: f"CIK-{acc}"}
        a_strict, s_strict = strict_decode(fid, props(fid, unit, tt), drv(name, bq), em)
        a_prod, s_prod = rebuild_anchor(fid, props(fid, unit, tt), drv(name, bq), em)
        assert {k: a_prod[k] for k in a_strict} == a_strict, f"parity broke for {fid}"
        assert s_prod == s_strict
        assert a_prod["concept_clue"] is None


def test_15_production_retains_all_probe_rejection_classes():
    """v4: NO coverage lost in the migration — the four existing rejection classes hold against
    the PRODUCTION function, plus the time_type validity check."""
    fid, _ = DI.build_id("SYN-ACC-K", "eps", period_id="gp_2024-01-01_2024-03-31",
                         surprise="actual_vs_consensus")
    with pytest.raises(ValueError, match="forbidden/unknown"):
        rebuild_anchor(fid, props(fid, "usd", "duration"), drv("eps", ("EPS of $ 1.23",)),
                       {"SYN-ACC-K": "C"})
    plain, _ = DI.build_id("SYN-ACC-K", "revenue", period_id="gp_2024-01-01_2024-12-31")
    with pytest.raises(ValueError, match="!= id driver"):
        rebuild_anchor(plain, props(plain, "m_usd", "duration"), drv("gross_margin", ("q",)),
                       {"SYN-ACC-K": "C"})
    bad = props(plain, "m_usd", "duration")
    bad["fact_scope"] = "period=gp_2020-01-01_2020-12-31"
    with pytest.raises(ValueError, match="stored fact_scope != id suffix"):
        rebuild_anchor(plain, bad, drv("revenue", ("q",)), {"SYN-ACC-K": "C"})
    with pytest.raises(ValueError, match="cross-wired or missing edge"):
        rebuild_anchor(plain, props(plain, "m_usd", "duration"), drv("revenue", ("q",)),
                       {"OTHER-ACC": "C"})
    with pytest.raises(ValueError, match="time_type"):
        rebuild_anchor(plain, props(plain, "m_usd", "garbage"), drv("revenue", ("q",)),
                       {"SYN-ACC-K": "C"})
    bad_driver = {"name": "revenue", "fact_type": "event",
                  "definitional_evidence": {"birth_quotes": ["q"]}}
    with pytest.raises(ValueError, match="not a metric Driver"):
        rebuild_anchor(plain, props(plain, "m_usd", "duration"), bad_driver, {"SYN-ACC-K": "C"})
    bogus = plain + "|bogus=1"
    with pytest.raises(ValueError, match="forbidden/unknown"):
        rebuild_anchor(bogus, props(bogus, "m_usd", "duration"), drv("revenue", ("q",)),
                       {"SYN-ACC-K": "C"})


def test_16_wording_law_stored_quote_is_the_only_fallback():
    """Empty birth_quotes → the STORED props['quote'] is the only fallback; blank/absent stored
    quote → fail closed; nonempty birth_quotes always win over the stored quote."""
    fid, _ = DI.build_id("SYN-ACC-L", "revenue", period_id="gp_2024-01-01_2024-12-31")
    em = {"SYN-ACC-L": "C"}
    a, _ = rebuild_anchor(fid, props(fid, "m_usd", "duration", quote="Total revenue $ 6,707"),
                          drv("revenue", ()), em)
    assert a["wording"] == ("Total revenue $ 6,707",), "stored quote must serve as the fallback"
    with pytest.raises(ValueError, match="blank wording"):
        rebuild_anchor(fid, props(fid, "m_usd", "duration"), drv("revenue", ()), em)
    with pytest.raises(ValueError, match="blank wording"):
        rebuild_anchor(fid, props(fid, "m_usd", "duration", quote="   "), drv("revenue", ()), em)
    b, _ = rebuild_anchor(fid, props(fid, "m_usd", "duration", quote="an LWW quote"),
                          drv("revenue", ("the birth quote",)), em)
    assert b["wording"] == ("the birth quote",), "birth_quotes are PRIMARY — fallback ignored"


def test_17_multiple_active_concept_resolutions_fail_closed():
    fid, _ = DI.build_id("SYN-ACC-M", "revenue", period_id="gp_2024-01-01_2024-12-31")
    em = {"SYN-ACC-M": "C"}
    d = drv("revenue", ("q",))
    with pytest.raises(ValueError, match="ACTIVE ConceptResolutions"):
        rebuild_anchor(fid, props(fid, "m_usd", "duration"), d, em,
                       concept_resolutions=("us-gaap:Revenues", "us-gaap:SalesRevenueNet"))
    a, _ = rebuild_anchor(fid, props(fid, "m_usd", "duration"), d, em,
                          concept_resolutions=("us-gaap:Revenues",))
    assert a["concept_clue"] == "us-gaap:Revenues"
    b, _ = rebuild_anchor(fid, props(fid, "m_usd", "duration"), d, em)
    assert b["concept_clue"] is None


def test_18_numeric_derived_from_stored_slots_zero_counts_unit_both_directions():
    """Numeric-ness derives from the STORED value slots (never caller-asserted): a stored ZERO
    is numeric (is-not-None law); numeric needs a NONBLANK unit; numberless needs
    series_unit=None — both directions fail closed."""
    fid, _ = DI.build_id("SYN-ACC-N", "weather_condition", period_id="gp_2024-01-01_2024-03-31")
    em = {"SYN-ACC-N": "C"}
    d = drv("weather_condition", ("unusually cold winter",))
    with pytest.raises(ValueError, match="numeric fact lacking nonblank series_unit"):
        rebuild_anchor(fid, props(fid, None, "duration", level_low=0), d, em)
    with pytest.raises(ValueError, match="numeric fact lacking nonblank series_unit"):
        rebuild_anchor(fid, props(fid, "   ", "duration", level_low=0), d, em)
    with pytest.raises(ValueError, match="numeric fact lacking nonblank series_unit"):
        rebuild_anchor(fid, props(fid, None, "duration", change_value=5), d, em)
    a, _ = rebuild_anchor(fid, props(fid, None, "duration"), d, em)
    assert a["series_unit"] is None, "numberless (all slots None) with series_unit=None is legal"
    with pytest.raises(ValueError, match="numberless fact must carry series_unit=None"):
        rebuild_anchor(fid, props(fid, "m_usd", "duration", level_low=None), d, em)


def test_19_smallest_missing_field_is_named():
    """Prove-or-stop: the error NAMES the smallest missing identity piece."""
    fid, _ = DI.build_id("SYN-ACC-O", "revenue", period_id="gp_2024-01-01_2024-12-31")
    d = drv("revenue", ("q",))
    for missing in ("fact_scope", "series_unit", "time_type"):
        p = props(fid, "m_usd", "duration")
        del p[missing]
        with pytest.raises(ValueError, match=missing):
            rebuild_anchor(fid, p, d, {"SYN-ACC-O": "C"})
    with pytest.raises(ValueError, match="bad id shape"):
        rebuild_anchor("not-a-du-id", props(fid, "m_usd", "duration"), d, {"SYN-ACC-O": "C"})


def test_20_malformed_clues_rejected_never_silently_repaired():
    """The LETTERS bug pinned: a bare-string birth_quotes ('Revenue') iterates into characters —
    must be REJECTED as malformed, never accepted as wording. Blank/non-string members and
    blank/non-string sole ConceptResolution clues are malformed too."""
    fid, _ = DI.build_id("SYN-ACC-P", "revenue", period_id="gp_2024-01-01_2024-12-31")
    em = {"SYN-ACC-P": "C"}
    p = props(fid, "m_usd", "duration")
    bare = {"name": "revenue", "fact_type": "metric",
            "definitional_evidence": {"birth_quotes": "Revenue"}}
    with pytest.raises(ValueError, match="malformed birth_quotes"):
        rebuild_anchor(fid, p, bare, em)
    with pytest.raises(ValueError, match="malformed birth_quotes"):
        rebuild_anchor(fid, p, drv("revenue", ("ok", "")), em)
    with pytest.raises(ValueError, match="malformed birth_quotes"):
        rebuild_anchor(fid, p, drv("revenue", ("ok", 3)), em)
    with pytest.raises(ValueError, match="malformed ConceptResolution"):
        rebuild_anchor(fid, p, drv("revenue", ("q",)), em, concept_resolutions=("",))
    with pytest.raises(ValueError, match="malformed ConceptResolution"):
        rebuild_anchor(fid, p, drv("revenue", ("q",)), em, concept_resolutions=(3,))


def test_21_injection_channels_stay_closed():
    """The removed caller-supplied channels must never return: no fact_quote argument (quote
    fallback = the STORED props['quote'] only) and no numeric_value_present flag (numeric-ness
    derives from the STORED value slots only)."""
    import inspect
    params = set(inspect.signature(rebuild_anchor).parameters)
    assert "fact_quote" not in params, "caller-supplied quote channel reintroduced"
    assert "numeric_value_present" not in params, "caller-asserted numeric flag reintroduced"
    assert params == {"fact_id", "props", "driver_node", "edge_map", "concept_resolutions"}


def test_22_all_five_value_slots_must_be_present():
    """Absent value-slot keys are MISSING DATA, never silently 'numberless' — explicit None is
    the only legal no-value. Each missing key is named (prove-or-stop)."""
    fid, _ = DI.build_id("SYN-ACC-Q", "revenue", period_id="gp_2024-01-01_2024-12-31")
    d = drv("revenue", ("q",))
    em = {"SYN-ACC-Q": "C"}
    bare = {"fact_scope": fid.split(":", 3)[3], "series_unit": None, "time_type": "duration"}
    with pytest.raises(ValueError, match="level_low"):
        rebuild_anchor(fid, bare, d, em)
    for slot in ("level_low", "level_high", "change_value", "comparison_low", "comparison_high"):
        p = props(fid, None, "duration")
        del p[slot]
        with pytest.raises(ValueError, match=slot):
            rebuild_anchor(fid, p, d, em)
    a, _ = rebuild_anchor(fid, props(fid, None, "duration"), d, em)
    assert a["series_unit"] is None, "all-present all-None + series_unit=None stays legal"


def test_23_blank_company_id_rejected():
    fid, _ = DI.build_id("SYN-ACC-R", "revenue", period_id="gp_2024-01-01_2024-12-31")
    d = drv("revenue", ("q",))
    p = props(fid, "m_usd", "duration")
    with pytest.raises(ValueError, match="blank company id"):
        rebuild_anchor(fid, p, d, {"SYN-ACC-R": ""})
    with pytest.raises(ValueError, match="blank company id"):
        rebuild_anchor(fid, p, d, {"SYN-ACC-R": "   "})
    with pytest.raises(ValueError, match="cross-wired or missing edge"):
        rebuild_anchor(fid, p, d, {"SYN-ACC-R": None})


def test_24_concept_clues_container_must_be_list_or_tuple():
    """The birth_quotes letters-bug class, sibling parameter: a bare string iterates into
    CHARACTERS ('R' was accepted as a clue; a long string failed for the WRONG reason); None
    crashed with TypeError. All must be clean ValueError rejections; a real list/tuple works."""
    fid, _ = DI.build_id("SYN-ACC-S", "revenue", period_id="gp_2024-01-01_2024-12-31")
    d = drv("revenue", ("q",))
    p = props(fid, "m_usd", "duration")
    em = {"SYN-ACC-S": "C"}
    for bad in ("R", "us-gaap:Revenues", None, 3):
        with pytest.raises(ValueError, match="expected list/tuple"):
            rebuild_anchor(fid, p, d, em, concept_resolutions=bad)
    a, _ = rebuild_anchor(fid, p, d, em, concept_resolutions=["us-gaap:Revenues"])
    assert a["concept_clue"] == "us-gaap:Revenues"


def test_25_input_schema_guard_malformed_inputs_raise_never_emit_or_crash():
    """Reproduced before fixing: driver_node/edge_map/definitional_evidence as strings CRASHED
    (AttributeError); padded ' C ' and int 123 were ACCEPTED as company; blank parsed source
    and driver names EMITTED anchors. All must be clean ValueError."""
    fid, _ = DI.build_id("SYN-ACC-T", "revenue", period_id="gp_2024-01-01_2024-12-31")
    d = drv("revenue", ("q",))
    p = props(fid, "m_usd", "duration")
    em = {"SYN-ACC-T": "C"}
    with pytest.raises(ValueError, match="props must be a mapping"):
        rebuild_anchor(fid, [("a", 1)], d, em)
    with pytest.raises(ValueError, match="driver_node must be a mapping"):
        rebuild_anchor(fid, p, "revenue", em)
    with pytest.raises(ValueError, match="edge_map must be a mapping"):
        rebuild_anchor(fid, p, d, "SYN-ACC-T")
    with pytest.raises(ValueError, match="definitional_evidence must be a mapping"):
        rebuild_anchor(fid, p, {"name": "revenue", "fact_type": "metric",
                                "definitional_evidence": "x"}, em)
    blank_src = "du: :revenue:period=gp_2024-01-01_2024-12-31"
    with pytest.raises(ValueError, match="blank source id"):
        rebuild_anchor(blank_src, {**p, "fact_scope": blank_src.split(":", 3)[3]}, d, {" ": "C"})
    blank_drv = "du:SYN-ACC-T: :period=gp_2024-01-01_2024-12-31"
    with pytest.raises(ValueError, match="blank driver name"):
        rebuild_anchor(blank_drv, {**p, "fact_scope": blank_drv.split(":", 3)[3]},
                       {"name": " ", "fact_type": "metric",
                        "definitional_evidence": {"birth_quotes": ["q"]}}, em)
    with pytest.raises(ValueError, match="nonblank, unpadded string"):
        rebuild_anchor(fid, p, d, {"SYN-ACC-T": " C "})
    with pytest.raises(ValueError, match="nonblank, unpadded string"):
        rebuild_anchor(fid, p, d, {"SYN-ACC-T": 123})
