"""Pass-1 CORE tests for ``canonicalize()`` — the §C pure 12-step function.

Covers Harness_BuilderPrompt.md §6 buckets:
  A. Shape / format DIRECT rejects → invalid_slug_shape (K1-K5, doubt #45)
  C. Word-order + plural/synonym fold (K27/K32/K33)
  D. Synonym / acronym / compound folds — ONLY pairs present in §F.2/§F.3/§F.4 (K34/K35, R6)
  E. Slot rules — slot_collision / no_metric / too_many_slots / shortcut / bare metric
     (K6, K22, K27, K29, R3, R8)

Every EXPECTED outcome is derived from the SPEC rule (DriverOntology_Implementation.md §C/§D/§D.1,
DriverOntology.md R3/R6/R8, req_canonical.md K-ids) and cited per-test, never guessed.
Asserts the Rejection.reason (and .token/.category where load-bearing) or the canonical string.
Pure offline; no LLM, no network. See Harness_BuilderPrompt.md §0a/§6/§7.
"""

from __future__ import annotations

import pytest

from driver_ids import canonicalize, Rejection
from vocab_seed import build_vocab_snapshot


@pytest.fixture(scope="module")
def vocab():
    """Frozen VocabSnapshot from the static §F.1-§F.9 seeds (build_vocab_snapshot)."""
    return build_vocab_snapshot()


# ─────────────────────────────────────────────────────────────────────────────
# Bucket A — DIRECT canonicalize() shape rejects → invalid_slug_shape
# (Harness_BuilderPrompt.md §6.A "A1 · DIRECT canonicalize()"; spec §C step 1 +
#  §D shape regex ^[a-z]([a-z0-9]|_(?!_))*[a-z0-9]$ ; doubt #45 "is the shape regex safe?")
# ─────────────────────────────────────────────────────────────────────────────

def test_A_camelcase_rejected(vocab):
    """K1 (case/format drift — CamelCase). §D shape regex starts with [a-z] and
    forbids uppercase; ``IPhoneChinaSales`` fails step-1 shape gate → invalid_slug_shape.
    (Harness §6.A A1; spec §C step 1.)"""
    r = canonicalize("IPhoneChinaSales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "invalid_slug_shape"


def test_A_doubled_underscore_rejected(vocab):
    """K4 (consecutive underscores). §D regex body is ``_(?!_)`` — a single underscore
    NOT followed by another; ``iphone__sales`` has a doubled underscore → invalid_slug_shape.
    (Harness §6.A; spec §C step 1 / §D "Rejects ``a__b``, ``foo__bar``".)"""
    r = canonicalize("iphone__sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "invalid_slug_shape"


def test_A_leading_underscore_rejected(vocab):
    """K4 (leading underscore). §D regex must START with [a-z]; ``_iphone_sales`` begins
    with ``_`` → invalid_slug_shape. (Harness §6.A; spec §D "Rejects ``_foo``".)"""
    r = canonicalize("_iphone_sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "invalid_slug_shape"


def test_A_trailing_underscore_rejected(vocab):
    """K4 (trailing underscore). §D regex must END with [a-z0-9]; ``iphone_sales_`` ends
    with ``_`` → invalid_slug_shape. (Harness §6.A; spec §D "Rejects ``foo_``".)"""
    r = canonicalize("iphone_sales_", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "invalid_slug_shape"


def test_A_hyphen_rejected_on_direct_call(vocab):
    """K2 (wrong separator — hyphen). canonicalize() does NOT slug() its input (that is the
    run_one/reuse entry point per Harness §6.A A2). On a DIRECT call the §D regex allows only
    [a-z0-9] + single underscore — hyphens are not in the body → ``iphone-china-sales`` fails
    the step-1 shape gate → invalid_slug_shape. (Harness §6.A "hyphen fails shape on a DIRECT call".)"""
    r = canonicalize("iphone-china-sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "invalid_slug_shape"


def test_A_non_ascii_rejected(vocab):
    """K3 (non-ASCII). §D regex char classes are ASCII [a-z]/[a-z0-9]; an accented byte
    (``iphoné_sales``) matches none → step-1 shape gate fails → invalid_slug_shape.
    (Harness §6.A "a non-ASCII input"; doubt #45.)"""
    r = canonicalize("iphoné_sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "invalid_slug_shape"


# ─────────────────────────────────────────────────────────────────────────────
# Bucket C — word-order + plural/synonym fold → exactly ONE canonical result
# (Harness_BuilderPrompt.md §6.C ; spec §C steps 5 (plural/synonym) → 9 (classify)
#  → 10 (order_by_slot, SLOT_ORDER theme→object→customer→geography→institution→metric);
#  DriverOntology.md R3 "the same set of tokens in any other order is the same name".)
# ─────────────────────────────────────────────────────────────────────────────

def test_C_word_order_china_iphone_sales(vocab):
    """K32 (word-order variant). Tokens china=geography, iphone=object, sales=metric reorder
    to SLOT_ORDER object→geography→metric → ``iphone_china_sales``. (Harness §6.C; spec §C
    step 10 order_by_slot; R3.)"""
    assert canonicalize("china_iphone_sales", vocab) == "iphone_china_sales"


def test_C_word_order_sales_iphone_china(vocab):
    """K27 (anchor/slot-order inversion — metric-first). Same 3 tokens in inverted order
    canonicalize to the SAME name ``iphone_china_sales`` (R3: order is not identity).
    (Harness §6.C "sales_iphone_china"; spec §C step 10.)"""
    assert canonicalize("sales_iphone_china", vocab) == "iphone_china_sales"


def test_C_plural_fold_then_reorder(vocab):
    """K33 (plural variant). step-5 plural map ``sale``→``sales`` (§F.3), THEN step-10 reorder
    → ``iphone_china_sales`` (sale→sales then reorder). (Harness §6.C "iphone_china_sale";
    spec §C step 5 plural_map + step 10.)"""
    assert canonicalize("iphone_china_sale", vocab) == "iphone_china_sales"


def test_C_plural_and_synonym_fold(vocab):
    """K33+K34 combined. step-5: ``iphones``→``iphone`` (§F.3 plural) AND ``topline``→``revenue``
    (§F.2 synonym); then reorder object→geography→metric → ``iphone_china_revenue``.
    (Harness §6.C "china_iphones_topline→iphone_china_revenue"; spec §C step 5 + step 10.)"""
    assert canonicalize("china_iphones_topline", vocab) == "iphone_china_revenue"


# ─────────────────────────────────────────────────────────────────────────────
# Bucket D — synonym / acronym / compound folds (ONLY pairs in §F.2/§F.3/§F.4)
# (Harness_BuilderPrompt.md §6.D ; DriverOntology.md R6 "compound metrics count as one slot".)
# ─────────────────────────────────────────────────────────────────────────────

def test_D_synonym_topline_to_revenue(vocab):
    """K34 (synonym). §F.2 SYNONYM_MAP ``topline``→``revenue`` (step 5); ``revenue`` is a bare
    valid metric → ACCEPT ``revenue``. (Harness §6.D "topline→revenue".)"""
    assert canonicalize("topline", vocab) == "revenue"


def test_D_acronym_gm_to_gross_margin(vocab):
    """K35 (acronym). §F.4 ACRONYM_MAP ``gm``→``gross_margin`` (step 5); ``gross_margin`` is a
    §F.6 COMPOUND_METRIC occupying ONE metric slot (R6) → ACCEPT ``gross_margin``.
    (Harness §6.D "gm→gross_margin".)"""
    assert canonicalize("gm", vocab) == "gross_margin"


def test_D_multi_token_sub_gross_profit_to_gross_margin(vocab):
    """K34 (multi-token synonym sub). §F.2 MULTI_TOKEN_SUBS ``gross_profit``→``gross_margin``
    applied at step-2 (substring, longest-match-first) → compound metric one slot (R6) →
    ACCEPT ``gross_margin``. (Harness §6.D "gross_profit→gross_margin".)"""
    assert canonicalize("gross_profit", vocab) == "gross_margin"


def test_D_data_center_multi_token_sub_then_no_metric(vocab):
    """K34 + K29. §F.2 MULTI_TOKEN_SUBS ``data_center``→``datacenter`` (step 2). ``datacenter``
    is an OBJECT, NOT a metric → after classify there is no metric slot → REJECT no_metric.
    Proves data_center is a multi-token sub AND that datacenter alone lacks a metric.
    (Harness §6.D "data_center→datacenter; datacenter alone→REJECTION no_metric"; spec §C step 11.)"""
    r = canonicalize("data_center", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "no_metric"


def test_D_acronym_fcf_compound_metric_accepts(vocab):
    """K35 (acronym to compound). §F.4 ``fcf``→``free_cash_flow`` (step 5); free_cash_flow is a
    §F.6 COMPOUND_METRIC = a bare metric occupying ONE slot (R6) → ACCEPT ``free_cash_flow``.
    (Harness §6.D "fcf→free_cash_flow ... bare metric accepts".)"""
    assert canonicalize("fcf", vocab) == "free_cash_flow"


def test_D_cloud_gross_margin_one_metric_slot(vocab):
    """R6 (compound = ONE slot). step-4.5 freeze rejoins ``gross``+``margin``→``gross_margin``
    (a §F.6 compound) so the bare ``margin``→``gross_margin`` synonym does NOT double-fold;
    cloud=theme + gross_margin=metric = 2 slots → ACCEPT ``cloud_gross_margin``.
    (Harness §6.D "cloud_gross_margin valid (gross_margin = ONE metric slot)"; spec §C step 4.5/8.5.)"""
    assert canonicalize("cloud_gross_margin", vocab) == "cloud_gross_margin"


# ─────────────────────────────────────────────────────────────────────────────
# Bucket E — slot rules
# (Harness_BuilderPrompt.md §6.E ; DriverOntology.md R3 (slot collision / fixed order),
#  R8 (length bound = MAX_EFFECTIVE_SLOTS=4); spec §C steps 8/9.5/10/11.)
# ─────────────────────────────────────────────────────────────────────────────

def test_E_two_geographies_slot_collision(vocab):
    """K27/R3 (doubt #13). china=geography AND japan=geography both classify to the geography
    slot → order_by_slot rejects two tokens in one slot → slot_collision (token=``geography``).
    (Harness §6.E "china_japan_sales→REJECT slot_collision"; spec §C step 10 / §D.1 order_by_slot.)"""
    r = canonicalize("china_japan_sales", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "slot_collision"
    assert r.token == "geography"


def test_E_no_metric(vocab):
    """K29 (missing metric). iphone=object + china=geography, no metric token → step-11
    metric-presence check fails → REJECT no_metric. (Harness §6.E "iphone_china→REJECT
    no_metric"; spec §C step 11.)"""
    r = canonicalize("iphone_china", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "no_metric"


def test_E_too_many_slots_five_distinct(vocab):
    """K6/R8 (length bound). ai=theme, datacenter=object, hyperscaler=customer, us=geography,
    capex=metric = 5 DISTINCT slots > MAX_EFFECTIVE_SLOTS(4) → REJECT too_many_slots. No
    collision (all distinct), so step-11 length check fires after step-10. (Harness §6.E
    "ai_datacenter_hyperscaler_us_capex→too_many_slots (5 DISTINCT slots)"; spec §C step 11 / §G.)"""
    r = canonicalize("ai_datacenter_hyperscaler_us_capex", vocab)
    assert isinstance(r, Rejection)
    assert r.reason == "too_many_slots"


def test_E_oil_price_shortcut_early_return(vocab):
    """K22-adjacent / R5. ``oil_price`` is a §F.1 SHORTCUTS_VOCAB entry → step-8 standalone
    shortcut early-return → ACCEPT ``oil_price`` (slot rules do not further apply).
    (Harness §6.E "oil_price→shortcut early-return"; spec §C step 8.)"""
    assert canonicalize("oil_price", vocab) == "oil_price"


def test_E_bare_revenue_accepts(vocab):
    """Bucket E (NOT K19/R9). A bare valid metric ``revenue`` (METRICS) occupies the single
    metric slot → ACCEPT ``revenue``. Over-genericity is R9 LLM-judgment (Layer-2 per K19
    split), NOT a canonicalize reject — so canonicalize MUST accept. (Harness §6.E "bare
    revenue→ACCEPT" + §6 K19-SPLIT note; spec §C steps 9-11.)"""
    assert canonicalize("revenue", vocab) == "revenue"
