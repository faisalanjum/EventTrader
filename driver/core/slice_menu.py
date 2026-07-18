"""S3 step-7 slice menu — frozen axis classification, the PIT company menu, FS-20
elimination handling, and the FS-18 exact fold, in ONE lawful place.

Law: FINAL_DESIGN §5.2 (:169-178) + STATUS R9. The axis→kind table below is the
FROZEN `CONFIRMED_AXES` table transcribed verbatim from
`.claude/plans/Drivers/Consolidation/XBRL_SliceAxis_Catalog.md` §2 (57 axes, 6
kinds; the catalog's ENTITY == the ID-law kind `entity_ownership`), refreshed
only offline through a governed update — never at runtime. NON_SLICE = the §3
name-liars (their members play no slice role). Runtime is the catalog §6 3-way
ladder: known slice axis → kind · known non-slice → skip · unknown → the
PROVISIONAL sentinel (never silently dropped; unknown values ENTER the menu for
later exact reuse).

FS-20 elimination guard (SEGMENT-FAMILY AXES ONLY — both the hard-exclude AND
the provisional rule): exact-qname lists, never a regex — materialized
2026-07-17 from a fresh read-only census (slice_axis_frozen.py,
OWNER-APPROVED 2026-07-17): 12 hand-vetted pure eliminations + 79 provisional
members; the
census-proven traps (GlobalPestElimination = a real Ecolab business,
Priortoelimination = a real gross) stay KEEP. A missed elimination falls to
KEEP (over-split-safe, FINAL_DESIGN:176); provisional quarantine is a
READ-layer concern. Correction is OFFLINE-ONLY (owner ruling 2026-07-17): the
structured exclusion logs are the evidence; a proven mistake is fixed by the
governed update simply MOVING the qname from the hard-exclude list to the
provisional list — no automatic demotion, no refresh engine.

XBRL link verification is FACT-LEVEL (match_xbrl_fact): the all-or-nothing
claim (concept + time_type + exact dates + complete dimension set, [] included)
must match an actual fact of the CURRENT filing — a member appearing elsewhere
in the filing proves nothing. Stored period ends are EXCLUSIVE (the verified
2026-07-09 decode ruling).

The company menu (FINAL_DESIGN:172) = union of members from all prior public
10-K/10-Q filings + slice values already used for that company, cut at ≤ the
event/source public time (PIT, :48). Retrieval is the adapter's job
(`get_company_slice_menu` — raw rows only); ALL law lives here."""
from datetime import date, timedelta

from driver.core.driver_ids import IdLawError, encode_unknown_axis
from driver.core.driver_member_fold import fold_target, member_token
from driver.core.slice_axis_frozen import (HARD_EXCLUDE_ELIMINATIONS,
                                           NON_SLICE_AXES, PROVISIONAL_MEMBERS)

__all__ = ["CONFIRMED_AXES", "NON_SLICE_AXES", "ELIMINATION_QNAMES",
           "PROVISIONAL_MEMBERS", "classify_axis", "build_menu",
           "check_member_refs", "match_xbrl_fact", "slice_tokens_from_scope"]

_SEG, _PRO, _GEO, _CUS, _CHA, _ENT = ("segment", "product", "geography",
                                      "customer", "channel", "entity_ownership")
CONFIRMED_AXES = {
    # SEGMENT (12)
    "us-gaap:StatementBusinessSegmentsAxis": _SEG,
    "us-gaap:SubsegmentsAxis": _SEG,
    "qdel:BusinessUnitAxis": _SEG,
    "cmcsa:BusinessUnitAxis": _SEG,
    "gtes:BusinessUnitAxis": _SEG,
    "cah:MedicalSegmentAxis": _SEG,
    "cah:PharmaceuticalSegmentAxis": _SEG,
    "oke:RegulatedSegmentByNameAxis": _SEG,
    "oke:ReportableSegmentByNameAxis": _SEG,
    "pru:DivisionAxis": _SEG,
    "emn:OtherSegmentsAxis": _SEG,
    "rxp:SegmentAxis": _SEG,                     # dormant shell — kept frozen
    # PRODUCT (12)
    "srt:ProductOrServiceAxis": _PRO,
    "atk:BrandAxis": _PRO,
    "ppl:RatesTypeAxis": _PRO,
    "khc:BrandsAxis": _PRO,
    "pep:BrandsAxis": _PRO,
    "pvh:BrandsAxis": _PRO,
    "www:BrandAxis": _PRO,
    "abbv:KeyProductPortfolioAxis": _PRO,
    "exas:ServiceOrProductTypeAxis": _PRO,
    "lpx:ProducttypeAxis": _PRO,
    "adsk:ContractWithCustomerResearchDevelopmentChannelAxis": _PRO,
    "blmn:RestaurantConceptAxis": _PRO,          # kind-corrected (was segment)
    # GEOGRAPHY (8)
    "srt:StatementGeographicalAxis": _GEO,
    "us-gaap:GeographicDistributionAxis": _GEO,
    "us-gaap:AirlineDestinationsAxis": _GEO,
    "hig:RegionsAxis": _GEO,
    "lear:RegionReportingInformationByRegionAxis": _GEO,
    "midd:RegionReportingInformationByRegionAxis": _GEO,
    "pg:GeographicLocationAxis": _GEO,
    "alk:InvestmentGeographicRegionAxis": _GEO,
    # CUSTOMER (5)
    "srt:MajorCustomersAxis": _CUS,
    "dy:CustomerTypeAxis": _CUS,
    "adi:RevenueFromContractWithCustomerEndMarketAxis": _CUS,
    "fn:ContractWithCustomerMarketCategoryAxis": _CUS,
    "ter:SeriesOfCustomerAxis": _CUS,            # dormant shell — kept frozen
    # CHANNEL (8)
    "us-gaap:ContractWithCustomerSalesChannelAxis": _CHA,
    "us-gaap:FranchisorDisclosureAxis": _CHA,
    "us-gaap:HealthCareOrganizationRevenueSourcesAxis": _CHA,
    "us-gaap:ContractWithCustomerBasisOfPricingAxis": _CHA,
    "mcd:SegmentReportingInformationBySecondarySegmentAxis": _CHA,
    "yum:FranchiseeOwnedStoresAxis": _CHA,
    "low:StoreTypeAxis": _CHA,
    "aap:NumberOfStoresAxis": _CHA,
    # ENTITY_OWNERSHIP (12)
    "dei:LegalEntityAxis": _ENT,
    "us-gaap:EquityMethodInvestmentNonconsolidatedInvesteeAxis": _ENT,
    "srt:ScheduleOfEquityMethodInvestmentEquityMethodInvesteeNameAxis": _ENT,
    "us-gaap:JointlyOwnedUtilityPlantAxis": _ENT,
    "us-gaap:IncomeStatementBalanceSheetAndAdditionalDisclosuresByDisposal"
    "GroupsIncludingDiscontinuedOperationsAxis": _ENT,
    "us-gaap:RealEstatePropertiesAxis": _ENT,
    "srt:OwnershipAxis": _ENT,
    "ppl:ByCompanyAxis": _ENT,
    "aes:DebtDefaultBySubsidiaryAxis": _ENT,
    "yum:CompanyOwnedStoresAxis": _ENT,          # kind-corrected (was channel)
    "fe:BusinessUnitsAxis": _ENT,                # kind-corrected (was segment)
    "tsco:ConsolidatedStoresAxis": _ENT,         # kind-corrected (was segment)
}

# FS-20 hard-exclude (SEGMENT-FAMILY AXES ONLY, per FINAL_DESIGN:176): the
# hand-vetted PURE eliminations from the 2026-07-17 read-only census — exact
# qnames, never a regex; the census-proven traps (GlobalPestElimination = a
# real Ecolab business, Priortoelimination = a real gross) stay KEEP. A proven
# mistake is corrected by the governed offline update moving its qname to the
# provisional list — nothing automatic.
ELIMINATION_QNAMES = HARD_EXCLUDE_ELIMINATIONS


def classify_axis(axis_qname):
    """Catalog §6 3-way ladder: ('slice', kind) | ('non_slice', None) |
    ('unknown', None). Never a regex, never a name heuristic at runtime."""
    if axis_qname in NON_SLICE_AXES:
        return ("non_slice", None)
    kind = CONFIRMED_AXES.get(axis_qname)
    return ("slice", kind) if kind else ("unknown", None)


def slice_tokens_from_scope(fact_scope):
    """The slice tokens of a stored fact_scope (build_id grammar: the `slice=`
    slot holds ';'-joined complete kind:value tokens)."""
    for slot in (fact_scope or "").split("|"):
        if slot.startswith("slice="):
            return set(slot[len("slice="):].split(";"))
    return set()


def _is_hard_excluded(status, kind, member):
    """FS-20 scope: the elimination guard applies ONLY on segment-family axes
    (FINAL_DESIGN:176) — the same qname elsewhere is not this guard's business."""
    return status == "slice" and kind == "segment" and member in ELIMINATION_QNAMES


def build_menu(xbrl_members, used_scopes):
    """The PIT company menu (FINAL_DESIGN:172): classified prior-filing members +
    already-used slice tokens → one exact-token set. FS-20 hard-excludes
    (segment-family axes only) are DROPPED with a structured log per exclusion
    (the self-heal feed); provisional members ENTER with a structured log (their
    quarantine is a READ-layer rule); non-slice members are skipped; unknown
    axes enter as their provisional sentinel. Returns (frozenset, logs)."""
    tokens, logs = set(), []
    for row in xbrl_members:
        status, kind = classify_axis(row["axis"])
        if status == "non_slice":
            continue
        if _is_hard_excluded(status, kind, row["member"]):
            logs.append({"event": "fs20_hard_exclude", "axis": row["axis"],
                         "member": row["member"], "label": row.get("label")})
            continue
        try:
            token = (member_token(kind, row["label"]) if status == "slice"
                     else encode_unknown_axis(row["axis"], row["label"]))
        except IdLawError as e:                    # unusable label: log, never guess
            logs.append({"event": "menu_label_unusable",
                         "axis": row["axis"], "member": row["member"],
                         "reason": str(e)})
            continue
        tokens.add(token)
        if (status == "slice" and kind == "segment"      # provisional rule is
                and row["member"] in PROVISIONAL_MEMBERS):  # segment-scoped too
            logs.append({"event": "fs20_provisional", "axis": row["axis"],
                         "member": row["member"], "token": token})
    for scope in used_scopes:
        tokens |= slice_tokens_from_scope(scope)
    return frozenset(tokens), logs


def _plus_day(iso):
    return (date.fromisoformat(iso) + timedelta(days=1)).isoformat()


def match_xbrl_fact(claim, fact_rows):
    """Fact-level XBRL verification: the input's all-or-nothing block claims
    'concept + time_type + exact date(s) + COMPLETE dimension set' — so a
    matching FACT must exist in the current filing with that exact period and
    exactly that dimension set (a member appearing elsewhere in the filing
    proves nothing; extra or missing dimensions fail; dims=[] is a claim too
    and must match a truly dimensionless fact). Stored XBRL period end is
    EXCLUSIVE (Fable ruling 2026-07-09, 140/140-verified): a duration matches
    when stored start == claimed start AND stored end == claimed end + 1 day;
    an instant stores its date in start_date and matches claimed end + 1 day.
    claim = {"time_type", "start", "end", "dims": {(axis, member), ...}};
    fact_rows = adapter rows. Returns the matched row's dims (with labels for
    token recompute) or None."""
    try:
        end_excl = _plus_day(claim["end"]) if claim["end"] else None
    except ValueError:
        return None
    for row in fact_rows:
        if claim["time_type"] == "duration":
            if (row["period_type"] != "duration"
                    or row["start_date"] != claim["start"]
                    or row["end_date"] != end_excl):
                continue
        else:
            if (row["period_type"] != "instant"
                    or row["start_date"] != end_excl):
                continue
        if {(d["axis"], d["member"]) for d in row["dims"]} == claim["dims"]:
            return row["dims"]
    return None


def check_member_refs(refs, fact_tokens, menu_tokens, matched_dims):
    """Ref-level law for one fact's member_refs, AFTER match_xbrl_fact proved
    the exact fact exists. The supplied slice_part is NEVER trusted: each
    (axis, member) must be one of the MATCHED FACT's own dimensions, and the
    slice_part must equal a token RECOMPUTED here from that dimension's label
    (frozen kind + shared normalizer, or the exact unknown-axis sentinel). It
    must also be one of the fact's own slice tokens. Any failure parks the
    fact (fail-closed). Returns (problems, notes, logs): notes carry the FS-18
    fold-vs-new verdict; logs carry structured current-fact exclusion events."""
    problems, notes, logs = [], [], []
    labels_by_pair = {}
    for d in matched_dims:
        labels_by_pair.setdefault((d["axis"], d["member"]), set()).add(d["label"])
    for ref in refs:
        axis, member, part = ref["axis"], ref["member"], ref["slice_part"]
        status, kind = classify_axis(axis)
        if status == "non_slice":
            problems.append(f"axis {axis} is NON-slice — its members play no "
                            f"slice role (catalog §3)")
            logs.append({"event": "non_slice_ref", "axis": axis,
                         "member": member, "where": "current_fact_ref"})
            continue                               # PARK + log (packet slice row)
        if _is_hard_excluded(status, kind, member):
            problems.append(f"member {member} is a pure elimination — FS-20 "
                            f"hard-exclude on a segment-family axis; an "
                            f"accounting construct is never a slice population")
            logs.append({"event": "fs20_hard_exclude", "axis": axis,
                         "member": member, "where": "current_fact_ref"})
            continue
        labels = labels_by_pair.get((axis, member))
        if not labels:
            problems.append(f"({axis}, {member}) is not a dimension of the "
                            f"matched fact — refs are never trusted, only "
                            f"verified against the exact fact")
            continue
        expected = set()
        for label in labels:
            try:
                expected.add(member_token(kind, label) if status == "slice"
                             else encode_unknown_axis(axis, label))
            except IdLawError:
                pass                               # unusable label can't verify
        if part not in expected:
            problems.append(f"slice_part {part!r} is not derivable from the "
                            f"filing's own label(s) for ({axis}, {member}) — "
                            f"supplied parts are never trusted")
            continue
        if part not in fact_tokens:
            problems.append(f"slice_part {part!r} supports no slice token of "
                            f"this fact ({sorted(fact_tokens) or 'none'})")
            continue
        notes.append({"slice_part": part, "member": member, "axis": axis,
                      "fold": fold_target(menu_tokens or frozenset(), part)
                      is not None})
    return problems, notes, logs
