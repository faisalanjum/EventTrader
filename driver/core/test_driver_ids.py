"""S3.1 fixed test vectors — frozen with the owner-approved ID law v1.0 (2026-07-16).

Every pinned value here was computed and approved BEFORE the implementation existed (TDD).
Never edit a pinned value; a change to any of them is an owner-level ID-law amendment.
"""
import pytest

from driver.core.driver_ids import (
    IdLawError,
    build_id,
    dec_canon,
    decode_unknown_axis,
    encode_unknown_axis,
    member_id,
    norm,
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


def test_member_id_never_stacks():
    bare, _ = build_id(SRC, "revenue", period_id=FY24)
    mem = member_id(bare, H2000)
    with pytest.raises(IdLawError):
        member_id(mem, H2000)
