"""S3.1 fixed test vectors — frozen with the owner-approved ID law v1.0 (2026-07-16).

Every pinned value here was computed and approved BEFORE the implementation existed (TDD).
Never edit a pinned value; a change to any of them is an owner-level ID-law amendment.
"""
import pytest

from driver.core.driver_ids import (
    SEC_CIK_10_PATTERN,
    IdLawError,
    build_id,
    dec_canon,
    decode_unknown_axis,
    encode_unknown_axis,
    graph_cik,
    member_id,
    norm,
    parse_period_id,
    probe_forms,
    signature_hash,
)

SRC = "0000320193-24-000123"
FY24 = "gp_2023-10-01_2024-09-28"
H2000 = "5371b939ac8e0a8c93991084e1f9c86b32fd809b87f3a54aff310b90512db9a1"


# ---- V1-V7: id + fact_scope assembly ----

def test_v1_metric_consolidated():
    fact_id, scope = build_id(SRC, "revenue", period_id=FY24)
    assert scope == f"period={FY24}"
    assert fact_id == f"du:{SRC}:revenue:period={FY24}"


def test_v2_single_slice():
    fact_id, scope = build_id(SRC, "revenue", period_id=FY24,
                              slice_parts=[("product", "iPhone")])
    assert scope == f"period={FY24}|slice=product:iphone"
    assert fact_id.endswith("|slice=product:iphone")


def test_v3_slice_sort():
    _, scope = build_id(SRC, "revenue", period_id=FY24,
                        slice_parts=[("segment", "Taco Bell"), ("geography", "China")])
    assert "slice=geography:china;segment:taco_bell" in scope


def test_v4_measurement_sort():
    _, scope = build_id(SRC, "revenue", period_id=FY24,
                        measurement_tokens=["constant currency", "Adjusted"])
    assert "measurement=adjusted,constant_currency" in scope


def test_v5_surprise_slot_order():
    _, scope = build_id(SRC, "revenue_surprise", period_id=FY24,
                        measurement_tokens=["Adjusted"],
                        surprise="actual_vs_consensus")
    assert scope == f"period={FY24}|measurement=adjusted|surprise=actual_vs_consensus"


def test_v6_sentinel_period():
    _, scope = build_id(SRC, "revenue_guidance", period_id="gp_ST")
    assert scope == "period=gp_ST"


def test_v7_empty_scope_keeps_trailing_colon():
    fact_id, scope = build_id("0001140361-23-000397", "workforce_reduction")
    assert scope == ""
    assert fact_id == "du:0001140361-23-000397:workforce_reduction:"


# ---- V8: unknown-axis sentinel round-trip ----

def test_v8_unknown_axis_roundtrip():
    part = encode_unknown_axis("custom:StoreTypeAxis", "Company-Operated Stores")
    assert part == ("unknown:xbrlaxis_637573746f6d3a53746f72655479706541786973"
                    "__company_operated_stores")
    qname, member = decode_unknown_axis(part)
    assert qname == "custom:StoreTypeAxis"
    assert member == "company_operated_stores"


def test_v8b_sentinel_survives_build_unmangled():
    part = encode_unknown_axis("custom:StoreTypeAxis", "Company-Operated Stores")
    kind, value = part.split(":", 1)
    _, scope = build_id(SRC, "revenue", period_id=FY24, slice_parts=[(kind, value)])
    assert f"slice={part}" in scope  # the structural __ must NOT be collapsed


# ---- V9-V11: OD-8 signature hash + collision member ----

def test_v10_signature_hash_pinned():
    sig = ["2000", "2000", "m_usd", None, None, None, None, None, None, None]
    assert signature_hash(sig) == H2000


def test_v11_null_differs_from_empty_string():
    all_null = signature_hash([None] * 10)
    empty_vt = signature_hash([None] * 8 + ["", None])
    assert all_null == "a6f025aa56fe7063e9216382083ec1f1d93898802e4a323e4b08d4742756566f"
    assert empty_vt == "78e6da8a99f306efd6c75e8fd951be9ac7a8e646fb327a60b7b338c1f29eb436"
    assert all_null != empty_vt


def test_v9_member_id_and_probe():
    bare, _ = build_id(SRC, "revenue", period_id=FY24)
    mem = member_id(bare, H2000)
    assert mem == f"{bare}|quote_hash={H2000}"
    exact, prefix = probe_forms(bare)
    assert exact == bare
    assert mem.startswith(prefix)


# ---- V12: decimal canonicalizer ----

@pytest.mark.parametrize("raw,canon", [
    ("2.50", "2.5"), ("1e3", "1000"), ("-0", "0"), ("-0.20", "-0.2"),
    ("1000.000", "1000"), (".5", "0.5"), ("0.100", "0.1"), ("-1.5E2", "-150"),
    (2000, "2000"), ("-0.000", "0"),
])
def test_v12_dec_canon(raw, canon):
    assert dec_canon(raw) == canon


# ---- V13: the one text normalizer ----

@pytest.mark.parametrize("raw,out", [
    ("Adjusted, Diluted", "adjusted_diluted"),
    ("Company-Operated Stores", "company_operated_stores"),
    ("Düsseldorf", "dusseldorf"),
    ("  GAAP  ", "gaap"),
    ("constant currency", "constant_currency"),
])
def test_v13_norm(raw, out):
    assert norm(raw) == out


def test_v13_norm_empty_result_rejected_in_build():
    with pytest.raises(IdLawError):
        build_id(SRC, "revenue", period_id=FY24, slice_parts=[("geography", "北京")])


# ---- V14 + fail-closed negatives ----

def test_v14_fiscal_mapped_form_accepted_colon_form_rejected():
    fact_id, _ = build_id("0000320193_24_000123", "revenue", period_id=FY24)
    assert fact_id.startswith("du:0000320193_24_000123:")
    with pytest.raises(IdLawError):
        build_id("0000320193:24:000123", "revenue", period_id=FY24)


@pytest.mark.parametrize("bad_source", ["", "a b", "x/y", "a|b", "acc=1"])
def test_bad_source_ids_rejected(bad_source):
    with pytest.raises(IdLawError):
        build_id(bad_source, "revenue", period_id=FY24)


@pytest.mark.parametrize("bad_name", ["", "r", "Revenue", "9lives", "a__b", "abc_", "a:b"])
def test_bad_driver_names_rejected(bad_name):
    with pytest.raises(IdLawError):
        build_id(SRC, bad_name, period_id=FY24)


@pytest.mark.parametrize("bad_period", [
    "gp_", "gp_2024-13-01_2024-12-31", "2024-01-01", "gp_UNKNOWN",
    "gp_2024-06-30_2024-04-01",   # end before start
    "gp_2024-06-30",              # single-date form retired by owner amendment 2026-07-16
])
def test_bad_period_ids_rejected(bad_period):
    with pytest.raises(IdLawError):
        build_id(SRC, "revenue", period_id=bad_period)


def test_v15_instant_is_date_twice():
    # Owner amendment 2026-07-16: the proven instant form gp_X_X is THE one-day form.
    fact_id, scope = build_id(SRC, "cash_and_equivalents",
                              period_id="gp_2024-06-30_2024-06-30")
    assert scope == "period=gp_2024-06-30_2024-06-30"
    assert fact_id.endswith(":cash_and_equivalents:period=gp_2024-06-30_2024-06-30")


def test_bad_slice_kind_and_bad_surprise_rejected():
    with pytest.raises(IdLawError):
        build_id(SRC, "revenue", period_id=FY24, slice_parts=[("brand", "x")])
    with pytest.raises(IdLawError):
        build_id(SRC, "revenue_surprise", period_id=FY24, surprise="beat")


def test_duplicate_parts_fold_to_one():
    _, scope = build_id(SRC, "revenue", period_id=FY24,
                        slice_parts=[("product", "iPhone"), ("product", "iphone")],
                        measurement_tokens=["Adjusted", "adjusted"])
    assert scope.count("product:iphone") == 1
    assert "measurement=adjusted" in scope and "adjusted,adjusted" not in scope


def test_signature_hash_fail_closed():
    with pytest.raises(IdLawError):
        signature_hash([None] * 9)                       # wrong arity
    with pytest.raises(IdLawError):
        signature_hash(["2.50", "2.5", "m_usd"] + [None] * 7)   # uncanonical number slot
    with pytest.raises(IdLawError):
        signature_hash([2000, "2000", "m_usd"] + [None] * 7)    # non-str number


def test_dec_canon_fail_closed():
    for bad in (1.5, "abc", "NaN", "Infinity", None):
        with pytest.raises(IdLawError):
            dec_canon(bad)


def test_num_canon_terminal_regime_rejects_every_float():
    # round-7 final rule: a float may have ALREADY lost source digits at parse time
    # (float('1.00000000000000000001') == 1.0) — exactness cannot be proven after the
    # fact, so floats are rejected wholesale at identity boundaries
    from decimal import Decimal
    from driver.core.driver_ids import num_canon
    for f in (0.3, 570.0, 0.1 + 0.2, float("nan"), 1.000000000000001):
        with pytest.raises(IdLawError, match="float|number"):
            num_canon(f)
    with pytest.raises(IdLawError):
        num_canon(True)
    # exact inputs pass through the strict canonicalizer unchanged
    assert num_canon(2000) == "2000"
    assert num_canon("2.50") == "2.5"
    assert num_canon(Decimal("1.00000000000000000001")) == "1.00000000000000000001"
    assert num_canon(Decimal("100000000000000000001")) == "100000000000000000001"


def test_neo4j_numeric_fidelity_within_the_declared_domain():
    # storage mapping (S3.5 paper): int -> Neo4j long (exact under 2^63);
    # Decimal -> float64 property — exact round-trip for <=15 significant digits
    from decimal import Decimal
    for text in ("1234567890123.45", "0.000123", "570", "-0.2", "99999999999999.9"):
        d = Decimal(text)
        assert Decimal(repr(float(d))) == d, text     # float64 round-trip is exact
    assert 999999999999999 < 2**63                    # 15-digit ints fit a long


def test_member_id_never_stacks():
    bare, _ = build_id(SRC, "revenue", period_id=FY24)
    mem = member_id(bare, H2000)
    with pytest.raises(IdLawError):
        member_id(mem, H2000)


def test_trailing_newline_rejected_across_every_identity_regex():
    """The $-anchor trap (reproduced live): re .match with $ accepts a FINAL
    newline — build_id minted 'du:SRC-1:revenue\n:' before the fullmatch fix.
    Every identity regex now uses exact full-string matching; nothing trims."""
    with pytest.raises(IdLawError):
        build_id("SRC-1\n", "revenue")                 # source id
    with pytest.raises(IdLawError):
        build_id("SRC-1", "revenue\n")                 # driver name (NAME-05)
    with pytest.raises(IdLawError):
        build_id("SRC-1", "revenue", period_id="gp_ST\n")   # period id
    with pytest.raises(IdLawError):
        member_id("du:s:rev:", "a" * 64 + "\n")        # quote hash
    with pytest.raises(IdLawError):
        decode_unknown_axis("unknown:xbrlaxis_61__x\n")     # sentinel decode


# ---- #827 B1 packet 4 (SEQ 299/301): the ONE NAME-17 suffix owner ----------

def test_827B4_split_terminal_suffix_pins():
    """NAME-17: only a TERMINAL `_guidance`/`_surprise` counts; strip exactly
    once. Five pins: no suffix · mid-name only · both terminals · stacked."""
    from driver.core.driver_ids import (GUIDANCE_SUFFIX, SURPRISE_SUFFIX,
                                        split_terminal_suffix)
    assert split_terminal_suffix("revenue") == ("revenue", None)
    assert split_terminal_suffix("gross_surprise_margin") == \
        ("gross_surprise_margin", None)          # mid-name never counts
    assert split_terminal_suffix("revenue_guidance") == \
        ("revenue", GUIDANCE_SUFFIX)
    assert split_terminal_suffix("revenue_surprise") == \
        ("revenue", SURPRISE_SUFFIX)
    assert split_terminal_suffix("x_guidance_surprise") == \
        ("x_guidance", SURPRISE_SUFFIX)          # STACKED: strip once only


# ---- #827 B8 (SEQ 339/340): the unknown-axis sentinel grammar fails closed ----
def test_827B8_encode_rejects_non_string_inputs():
    for bad_axis in (123, b"x", None):
        with pytest.raises(IdLawError, match="must be a string"):
            encode_unknown_axis(bad_axis, "Thing")
    with pytest.raises(IdLawError, match="must be a string"):
        encode_unknown_axis("us-gaap:SegmentAxis", 123)


@pytest.mark.parametrize('axis', [
    pytest.param(' ', id='blank'),
    pytest.param('a:b:c', id='two-colons'),
    pytest.param(':x', id='empty-prefix'),
    pytest.param('x:', id='empty-local'),
], )
def test_827B8_encode_rejects_non_qname_axes(axis):
    with pytest.raises(IdLawError, match="not a lawful XML QName"):
        encode_unknown_axis(axis, "Thing")


def test_827B8_decode_rejects_non_strings_and_bad_bytes():
    for bad in (123, None):
        with pytest.raises(IdLawError, match="must be a string"):
            decode_unknown_axis(bad)
    # SEQ 341: two separate truthful reasons — malformed hex vs undecodable bytes
    with pytest.raises(IdLawError, match="malformed lowercase UTF-8 hex"):
        decode_unknown_axis("unknown:xbrlaxis_abc__x")     # odd-length hex
    with pytest.raises(IdLawError, match="decoded bytes are not valid UTF-8"):
        decode_unknown_axis("unknown:xbrlaxis_ff__x")      # lawful hex, not UTF-8


def test_827B8_decode_accepts_only_the_complete_frozen_token():
    # SEQ 343: no bare-value compatibility path — one public grammar
    with pytest.raises(IdLawError, match="not an unknown-axis sentinel"):
        decode_unknown_axis("xbrlaxis_61__x")


@pytest.mark.parametrize('hexpart', [
    pytest.param('gg', id='non-hex'),
    pytest.param('FF', id='uppercase-hex'),
], )
def test_827B8_decode_structural_lowercase_hex_contract(hexpart):
    # SEQ 344: the frozen contract says LOWERCASE hex — non-hex and uppercase are
    # refused STRUCTURALLY by the sentinel grammar itself
    with pytest.raises(IdLawError, match="not an unknown-axis sentinel"):
        decode_unknown_axis(f"unknown:xbrlaxis_{hexpart}__x")


@pytest.mark.parametrize('raw', [
    pytest.param('a:b:c', id='two-colons'),
    pytest.param(':x', id='empty-prefix'),
    pytest.param('x:', id='empty-local'),
], )
def test_827B8_decode_rejects_invalid_decoded_qnames(raw):
    bad = "unknown:xbrlaxis_" + raw.encode().hex() + "__x"
    with pytest.raises(IdLawError, match="unlawful QName"):
        decode_unknown_axis(bad)


@pytest.mark.parametrize('member', [
    pytest.param('_x', id='leading-underscore'),
    pytest.param('x_', id='trailing-underscore'),
    pytest.param('x__y', id='double-underscore'),
], )
def test_827B8_decode_rejects_non_normalized_member_halves(member):
    with pytest.raises(IdLawError, match="not normalized"):
        decode_unknown_axis("unknown:xbrlaxis_61__" + member)


@pytest.mark.parametrize('value', [
    pytest.param(123, id='int'),
    pytest.param(b'x', id='bytes'),
], )
def test_827B8_build_id_unknown_slice_rejects_non_strings(value):
    # SEQ 342: non-reserved non-strings reach the EXISTING norm owner — its reason,
    # no duplicate type guard in _slice_value
    with pytest.raises(IdLawError, match=r"norm\(\) needs str"):
        build_id("src-1", "revenue", slice_parts=[("unknown", value)])


@pytest.mark.parametrize('value, inner', [
    pytest.param('xbrlaxis_abc__x', 'malformed lowercase UTF-8 hex', id='odd-hex'),
    pytest.param('xbrlaxis_ff__x', 'not valid UTF-8', id='invalid-utf8'),
    pytest.param('xbrlaxis_' + 'a:b:c'.encode().hex() + '__x', 'unlawful QName',
                 id='decoded-invalid-qname'),
    pytest.param('xbrlaxis_61___x', 'not normalized', id='non-normalized-member'),
], )
def test_827B8_build_id_rejects_malformed_reserved_sentinels(value, inner):
    # a malformed attempt at the reserved code-only sentinel must REJECT — it must
    # never fall through and normalize into a different value. SEQ 345: the boundary
    # message must CARRY the decoder's specific inner reason, not merely reject.
    with pytest.raises(IdLawError, match=f"malformed reserved.*{inner}"):
        build_id("src-1", "revenue", slice_parts=[("unknown", value)])


def test_827B8_must_allow_twins():
    # prefixed, unprefixed, and prefixed-UNICODE QNames (both halves non-ASCII);
    # free text; byte-identical reserved sentinel — exact equality, no containment
    assert decode_unknown_axis(encode_unknown_axis("us-gaap:SegmentAxis", "Cloud Revenue")) \
        == ("us-gaap:SegmentAxis", "cloud_revenue")
    assert decode_unknown_axis(encode_unknown_axis("Revenue", "Thing")) == ("Revenue", "thing")
    assert decode_unknown_axis(encode_unknown_axis("Ü:名", "Thing")) == ("Ü:名", "thing")
    _fid, scope = build_id("src-1", "revenue",
                           slice_parts=[("unknown", "Cloud Revenue")])
    assert scope == "slice=unknown:cloud_revenue"
    sentinel = encode_unknown_axis("custom:StoreTypeAxis", "Company-Operated Stores")
    _fid2, scope2 = build_id("src-1", "revenue",
                             slice_parts=[("unknown", sentinel.split(":", 1)[1])])
    assert scope2 == f"slice={sentinel}"


def test_827B7_parse_period_id_owner_pins():
    """THE one period-id parser (#827 B7): (start, end) text for dated ids,
    (None, None) for the four sentinels, IdLawError for everything else."""
    from driver.core.driver_ids import (IdLawError, PERIOD_SENTINEL_SCOPE,
                                        parse_period_id)
    assert parse_period_id("gp_2025-07-01_2025-09-30") == ("2025-07-01", "2025-09-30")
    assert parse_period_id("gp_2025-07-01_2025-07-01") == ("2025-07-01", "2025-07-01")
    for pid in PERIOD_SENTINEL_SCOPE:
        assert parse_period_id(pid) == (None, None)
    for bad in (123, None, b"gp_ST",                       # never a non-string
                "gp_2025-13-01_2025-09-30",                # impossible calendar
                "gp_2025-07-01_2025-06-30",                # reversed order
                "gp_2025-07-01x", "gp_ST ", "GP_ST", ""):  # malformed spellings
        with pytest.raises(IdLawError):
            parse_period_id(bad)


def test_827B9_surprise_scope_owner_pins_STRUCTURAL():
    """#827 B9 STRUCTURAL single-owner/closure proof — NOT a behavioral RED:
    production already returned all three lawful outcomes; the defect was the
    same contract spelled independently in two modules with no derivation
    link. THE one immutable pair->scope owner (FINAL_DESIGN OD-21) and the
    identity-gate vocabulary derived from its values, pinned both ways."""
    import types
    from driver.core import driver_ids as I
    assert isinstance(I.SURPRISE_SCOPE_BY_PAIR, types.MappingProxyType)
    assert dict(I.SURPRISE_SCOPE_BY_PAIR) == {
        ("actual", "consensus"): "actual_vs_consensus",
        ("actual", "previous_guidance"): "actual_vs_guidance",
        ("guidance", "consensus"): "guidance_vs_consensus",
    }
    with pytest.raises(TypeError):                 # immutable: no write door
        I.SURPRISE_SCOPE_BY_PAIR[("x", "y")] = "z"
    assert I._SURPRISE_TYPES == frozenset(I.SURPRISE_SCOPE_BY_PAIR.values())
    assert len(I._SURPRISE_TYPES) == 3             # values pairwise distinct
    # SEQ 353: the four frozen-contract basis/baseline constants ARE the map's
    # keys — one spelling for every consumer (F7, home suffix, CLI wiring,
    # DU-05 pair, period-lane cell). Values cited to FINAL_DESIGN :152 only.
    assert I.ACTUAL_BASIS == "actual"
    assert I.GUIDANCE_BASIS == "guidance"
    assert I.CONSENSUS_BASELINE == "consensus"
    assert I.PREVIOUS_GUIDANCE_BASELINE == "previous_guidance"
    assert set(I.SURPRISE_SCOPE_BY_PAIR) == {
        (I.ACTUAL_BASIS, I.CONSENSUS_BASELINE),
        (I.ACTUAL_BASIS, I.PREVIOUS_GUIDANCE_BASELINE),
        (I.GUIDANCE_BASIS, I.CONSENSUS_BASELINE),
    }


def test_827B13_build_period_id_constructs_what_the_one_parser_accepts():
    """#827 B13: the construction SPELLING owner — a pure constructor, not a
    validation boundary. Its lawful output is exactly what parse_period_id
    accepts; every refusal stays the parser's and each caller's existing
    boundary, so no second boundary is pinned here."""
    from driver.core.driver_ids import build_period_id, parse_period_id
    pid = build_period_id("2025-07-01", "2025-09-30")
    assert pid == "gp_2025-07-01_2025-09-30"
    assert parse_period_id(pid) == ("2025-07-01", "2025-09-30")
    same = build_period_id("2025-07-01", "2025-07-01")      # lawful one-day
    assert parse_period_id(same) == ("2025-07-01", "2025-07-01")


def test_827B11_slice_kind_owner_pins_STRUCTURAL():
    """#827 B11 STRUCTURAL single-owner proof (SEQ 358 design: seven NAMED
    constants, no ordered tuple). The seven frozen words pinned
    INDEPENDENTLY (spelled here, never read back from the owner), and the
    two derived frozen sets. FINAL_DESIGN §5.2 :169-178 (six kinds) +
    :174 (the unknown sentinel kind)."""
    from driver.core import driver_ids as I
    assert I.SEGMENT_KIND == "segment"
    assert I.PRODUCT_KIND == "product"
    assert I.GEOGRAPHY_KIND == "geography"
    assert I.CUSTOMER_KIND == "customer"
    assert I.CHANNEL_KIND == "channel"
    assert I.ENTITY_OWNERSHIP_KIND == "entity_ownership"
    assert I.UNKNOWN_SLICE_KIND == "unknown"
    assert I.KNOWN_SLICE_KINDS == frozenset({
        "segment", "product", "geography", "customer", "channel",
        "entity_ownership"})
    assert I.SLICE_KINDS == I.KNOWN_SLICE_KINDS | {"unknown"}
    assert len(I.SLICE_KINDS) == 7


def test_827B11_build_id_all_six_known_kinds_and_the_sentinel():
    """Acceptance side: every known kind passes the identity gate; the
    structurally valid unknown sentinel still round-trips (827B8 law)."""
    for kind in ("segment", "product", "geography", "customer", "channel",
                 "entity_ownership"):
        _fid, scope = build_id("src-1", "revenue",
                               slice_parts=[(kind, "US")])
        assert scope == f"slice={kind}:us"
    sentinel = encode_unknown_axis("custom:StoreTypeAxis", "Stores")
    _fid2, scope2 = build_id("src-1", "revenue",
                             slice_parts=[("unknown",
                                           sentinel.split(":", 1)[1])])
    assert scope2 == f"slice={sentinel}"


def test_827B11_build_id_rejects_bogus_case_and_padding():
    # SEQ 361: unhashable kinds ([], {}, bytearray) crashed raw TypeError at
    # the frozenset membership pre-fix — the string gate must refuse them too
    for bad in ("brand", "Segment", "segment ", "SEGMENT", "",
                [], {}, bytearray(b"segment")):
        with pytest.raises(IdLawError, match="unknown slice kind"):
            build_id("src-1", "revenue", slice_parts=[(bad, "US")])


def test_827B9_build_id_surprise_lawful_string_twins():
    """All three lawful words through the PUBLIC door: the slot lands verbatim,
    distinct words -> distinct ids; None stays the only lawful absence."""
    from driver.core.driver_ids import SURPRISE_SCOPE_BY_PAIR
    ids = set()
    for word in SURPRISE_SCOPE_BY_PAIR.values():
        fid, scope = build_id("src-1", "revenue_surprise", surprise=word)
        assert scope == f"surprise={word}"
        ids.add(fid)
    assert len(ids) == 3
    _fid, scope = build_id("src-1", "revenue_surprise", surprise=None)
    assert scope == ""


def test_827B9_build_id_surprise_non_string_is_IdLawError_never_TypeError():
    """SEQ-351 public RED (a REAL pre-fix behavioral defect): surprise=[] and
    surprise={} crashed TypeError at the frozenset membership; a set survived
    only by CPython's set-in-set coincidence. LAW: every non-string surprise
    raises the existing IdLawError — the string gate, never a crash — with
    None as the only lawful absence."""
    for bad in ([], {}, set(), ["actual_vs_consensus"],
                {"actual_vs_consensus": 1}, {"actual_vs_consensus"},
                frozenset({"actual_vs_consensus"}), 5, 0, True,
                b"actual_vs_consensus", ("actual", "consensus")):
        with pytest.raises(IdLawError, match="bad surprise type"):
            build_id("src-1", "revenue_surprise", surprise=bad)


# 827 Packet 17 — the SEC CIK lexical contract. The standards citations live
# beside the production owner in driver_ids, not restated here.


@pytest.mark.parametrize("value", ["0000320193", "0000000001", "9999999999"])
def test_graph_cik_accepts_the_lawful_twins(value):
    """Minimum, ordinary and maximum ten-digit CIKs all resolve unchanged."""
    assert graph_cik(value) == value


def test_graph_cik_refuses_the_non_registrant_marker():
    """THE GAP THIS PACKET CLOSES. `[0-9]{10}` alone accepts 0000000000, and
    both normalisers then map it to company `0` — inventing an entity rather
    than refusing. XBRL Guide §3.1.3 makes it a non-registrant marker, and this
    owner names an ACTUAL Company, so it must refuse."""
    assert graph_cik("0000000000") is None


@pytest.mark.parametrize("value,why", [
    ("١٢٣٤٥٦٧٨٩٠", "Arabic-Indic digits: str.isdigit() says True and Cypher "
                    "toInteger coerces them to 1234567890 — ANOTHER company"),
    ("³000000000", "superscript three also satisfies str.isdigit()"),
    ("-000000005", "sign survives zfill(10)"),
    ("       320", "whitespace survives zfill(10)"),
    ("0000003e10", "exponent text: Cypher coerces it to 30000000000"),
    ("", "empty"),
    ("12345678901", "eleven digits: zfill does not truncate"),
    ("320193", "the ARCHIVE spelling is not the Company spelling"),
])
def test_graph_cik_refuses_every_malformed_twin(value, why):
    assert graph_cik(value) is None, why


@pytest.mark.parametrize("value", [None, 1, b"0000320193", ["0000320193"]])
def test_graph_cik_refuses_non_strings(value):
    assert graph_cik(value) is None


def test_python_matches_the_pattern_as_a_whole_value():
    """PYTHON ONLY. A trailing newline must not pass, because Python's `$`
    matches before a final newline — so this rule is sound only as a whole-value
    match. This proves nothing about Cypher; the same predicate is proved
    against the real engine by the parameterized read-only Neo4j test, which
    carries the trailing-newline case too."""
    import re
    assert re.fullmatch(SEC_CIK_10_PATTERN, "0000320193")
    assert not re.fullmatch(SEC_CIK_10_PATTERN, "0000320193\n")
    assert graph_cik("0000320193\n") is None


# 827: the period-id grammar is ASCII, and its refusal must say so.
_FULLWIDTH_PERIOD = "gp_２０２５-０７-０１" \
                    "_２０２５-０９-３０"
_ARABIC_PERIOD = "gp_٢٠٢٥-٠٧-٠١" \
                 "_٢٠٢٥-٠٩-٣٠"


@pytest.mark.parametrize("bad", [_FULLWIDTH_PERIOD, _ARABIC_PERIOD])
def test_a_unicode_digit_period_id_is_MALFORMED_not_an_impossible_date(bad):
    """Python's `\\d` matches every Unicode decimal digit, so these passed the
    grammar and were refused later by `date.fromisoformat` as an "impossible
    calendar date". That reason is untrue — they are lawful dates in another
    script. What they violate is the frozen ASCII spelling of an INTERNAL id,
    so they must take the malformed path and say so."""
    with pytest.raises(IdLawError, match="bad period id"):
        parse_period_id(bad)


@pytest.mark.parametrize("bad", [_FULLWIDTH_PERIOD, _ARABIC_PERIOD])
def test_the_same_refusal_reaches_the_build_id_caller(bad):
    with pytest.raises(IdLawError, match="bad period id"):
        build_id(SRC, "revenue", period_id=bad)


def test_the_LAWFUL_ascii_period_twin_still_parses_and_builds():
    """MUST-ALLOW twin: the fix narrows the grammar and nothing else."""
    assert parse_period_id("gp_2025-07-01_2025-09-30") == \
        ("2025-07-01", "2025-09-30")
    assert build_id(SRC, "revenue", period_id="gp_2025-07-01_2025-09-30")


def test_T6_the_minimal_fact_id_reader_lives_at_the_owner():
    """T6 (#827 F-VALID): reading the source_id back off a du: fact id is the
    GRAMMAR OWNER's job — the validators' local split is gone. Two minimal
    readers at one owner (this + D2's slice reader), never a generic parser."""
    import inspect
    from driver.core.driver_ids import IdLawError, fact_source_id
    import driver.core.driver_validators as dv
    assert fact_source_id("du:0000320193-24-000123:revenue:s0") == \
        "0000320193-24-000123"
    for bad in (None, "", "x:y", "du:only:three", "xu:a:b:c"):
        try:
            fact_source_id(bad)
            assert False, f"accepted {bad!r}"
        except IdLawError:
            pass
    src = inspect.getsource(dv._id_rebuild)
    assert ".split(" not in src, "the validators re-grew a local id parse"
