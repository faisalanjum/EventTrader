# XBRL Slice-Axis Catalog — the frozen `CONFIRMED_AXES` table (100% coverage)

**What this is:** the complete, exact list of every XBRL dimension (axis) in the EventMarketDB graph that is a **business slice** — i.e. a real cube dimension for bifurcating a `DriverUpdate` (`fact_scope`). Plus the elimination guard, the coverage proof, and the runtime table.

**Snapshot:** built 2026-06-26 from the live Neo4j XBRL graph (read-only). Reproducible — every query is inlined below. This is a *point-in-time* census; new filers coin new axes, which the runtime **sentinel** catches (see §6).

**The slice test (how every axis below was judged):** an axis is a slice only if each **member** is a real business population you can prefix with *"revenue/earnings from ___"* — a **segment · product · geography · customer · channel · entity**. Everything else (measurement, instrument, plan, tax, reconciling/elimination) is accounting, not a business split. `period` and `basis` are handled separately, **not** as slice axes.

---

## How to read this (cold-start bot — START HERE)

This folder builds the **Driver catalog**: it turns scattered per-company causes into **one graded, cross-company, queryable history of what moves stocks → learn → predict → trade**. Slices keep the *same cause shared across companies* while recording *which part of the business* a fact is about — without that, brands fragment the cause and cross-company comparison dies. (Why, in full: `README.md`.)

Two docs own the slice/XBRL work — read in this order:

| Doc | Owns | Read it for |
|---|---|---|
| **`Naming_Slices_XBRL.md`** | the **SPEC** — the one law (over-merge=never, over-split=ok), asymmetric authority (LLM keeps/provisional/coins; CODE alone deletes/merges), `fact_scope = period + slice + measurement`, the frozen-table/sentinel, the menu, within-company reconciliation, the elimination guard, autonomy/self-improvement, the cross-company caveat, all 33 rules. | **HOW & WHY** (the mechanism) |
| **`XBRL_SliceAxis_Catalog.md`** *(this doc)* | the **DATA** — the actual axis→kind list, the census numbers, real member examples, the elimination qname tiers, the "name-liar" non-slices, provenance. | **WHAT** — the contents that fill the spec's frozen `SLICE_AXES` (`Naming_Slices §6` DATA SLOT) + `ELIMINATION_QNAMES` (`§10` guard) |

Other siblings: `FactScope_IdentityDecision_PENDING.md` (owner decision package on identity/linking), `MetricGuidanceFamily.md` (metric/guidance/surprise/action family = `BASE_METRIC`), `GuidancePeriod.md` (period), `UnitExtraction.md` (units + per-X naming). Schema source of truth = `../WIP/DriverGraphSchema.md`. Session memory slug: `project_xbrl_cube_dimensions`.

> **Everything in §2–§6 below is the empirical DATA only.** For *why* a thing is a slice, the runtime rule, the sentinel, autonomy, etc. — the authoritative text is `Naming_Slices_XBRL.md`; sections here that restate mechanism (§4 guard, §6 runtime) are short summaries, not the source of truth.

---

## 1. Universe & coverage (the 100% claim)

| Set | Count | Status |
|---|---|---|
| Distinct axes declared | **2,344** | 341 standard + 2,003 company-coined |
| Axes actually **used on a fact** | **143** | 102 standard + 41 coined — *the operative universe* |
| Facts carrying any dimension | 35,968 of 9.93M (0.4%) | shallow: 86% carry 1 axis |
| **SLICE axes (this catalog)** | **≈55** | all adversarially verified: 17 std (12 used + ~5 declared) + 5 coined-used + ~31 coined-swept (`wf_07c1c51b`: 32 survived incl. 6 kind-corrected, 2 demoted). 2 are **dormant shells** (rxp:Segment, ter:SeriesOfCustomer — 0 members, 0 use; kind from axis-name + domain-root) |

**Coverage statement (honest):**
- ✅ **100% of standard axes (341)** classified (prior census + adversarial audit `wf_8d0398a1`).
- ✅ **100% of used axes (143)** classified → **17 are slices**, residual 0.
- ✅ **100% of slice-name coined candidates (82)** classified here (members pulled, name-lies caught).
- ⚠️ **Residual:** a coined axis that is BOTH currently-unused (0 facts) AND oddly-named (no segment/brand/product/region/customer/channel word). Such an axis produces no `DriverUpdate` today; if it ever appears on a fact the **sentinel** routes it to *provisional* (never lost). So the gap is operationally moot by construction.

---

## 2. The SLICE axes, grouped by cube dimension

**At a glance — the 6 cube dimensions and how many XBRL tags feed each:**

| Cube dimension | # tags | Plain meaning — *"revenue/earnings from ___"* | Example tags |
|---|---:|---|---|
| **segment** | 12 | a business unit / operating segment the company **runs as** | `StatementBusinessSegments`, `BusinessUnit`, `Division` |
| **product** | 12 | a product / brand / service it **sells** | `ProductOrService`, Brands (`khc`,`pep`,`pvh`,`www`), `KeyProductPortfolio` |
| **geography** | 8 | a region / country it **operates in** | `StatementGeographical`, `Regions`, `GeographicLocation` |
| **customer** | 5 | a customer / end-market it **sells to** | `MajorCustomers`, `CustomerType`, `EndMarket` |
| **channel** | 8 | **how** it sells / runs (franchised vs company-operated) | `SalesChannel`, `Franchisor`, `StoreType` |
| **entity** | 12 | a legal entity / JV / subsidiary it **owns a stake in** | `LegalEntity`, `EquityMethod`/JV, `ByCompany` |
| **TOTAL** | **57** | the 6 slice axes (55 active; 2 are dormant shells) | — |

**Why many tags per axis:** different companies use different XBRL tags for the same idea — "segment" appears as `BusinessSegments` at one filer, `BusinessUnit` at another, `Division` at a third. The catalog's job is to point all of them at the **one** right axis. *(Full `fact_scope` = these 6 slices **+ period + measurement** = 8 separators total; period & measurement are governed elsewhere, not this catalog.)*

The full per-tag detail (every axis, with status + member examples) follows below.

---

**All rows below are adversarially VERIFIED.** Legend: `✓` = verified (audit `wf_8d0398a1` for standard + used-coined; sweep verify `wf_07c1c51b` for the coined ones). `✓ (was X)` = verified slice whose kind was **corrected** from the inline guess. `(weak)` = thin signal (1–2 members) → treat as provisional. `name+domain · 0 members, 0 use` = a **dormant shell** (axis declared but never populated); kind inferred from the axis name + its domain root — there are no members to verify, and the sentinel covers it if ever activated.

### SEGMENT — business unit / operating segment / division
| Axis | NS | Status | Member examples |
|---|---|---|---|
| `us-gaap:StatementBusinessSegmentsAxis` | std | ✓ · used 1074 | OliveGarden, EMEASegment |
| `us-gaap:SubsegmentsAxis` | std | ✓ · declared | FabricCare, GreaterChina |
| `qdel:BusinessUnitAxis` | coined | ✓ · used 16 | Labs, PointOfCare, MolecularDiagnostics |
| `cmcsa:BusinessUnitAxis` | coined | ✓ | ConnectivityAndPlatforms, ContentExperiences |
| `gtes:BusinessUnitAxis` | coined | ✓ | RussianBusinessUnit, MiddleEast |
| `cah:MedicalSegmentAxis` | coined | ✓ | MedicalDistributionAndProducts |
| `cah:PharmaceuticalSegmentAxis` | coined | ✓ | PharmaDistribution, NuclearPrecisionHealth |
| `oke:RegulatedSegmentByNameAxis` | coined | ✓ | NaturalGasLiquidsRegulated |
| `oke:ReportableSegmentByNameAxis` | coined | ✓ | NGL, NaturalGasPipelines |
| `pru:DivisionAxis` | coined | ✓ | PGIM, USBusinesses, IntlInsurance |
| `emn:OtherSegmentsAxis` | coined | ✓ | AdvancedMaterials, GrowthInitiatives |
| `rxp:SegmentAxis` | coined | name+domain · **0 members, 0 use** | domain=`AllSegments` (dormant shell — no member breakdown ever captured) |

### PRODUCT — product / brand / service line
| Axis | NS | Status | Member examples |
|---|---|---|---|
| `srt:ProductOrServiceAxis` | std | ✓ · used 757 | Frozen, Snacks, Foodservice |
| `atk:BrandAxis` | coined | ✓ · used 2 | Atkins, Quest, OWYN |
| `ppl:RatesTypeAxis` | coined | ✓ · used 2 (weak) | Electric, Gas |
| `khc:BrandsAxis` | coined | ✓ | Kraft, MaxwellHouse, Velveeta, Philadelphia |
| `pep:BrandsAxis` | coined | ✓ | Rockstar, BeCheery |
| `pvh:BrandsAxis` | coined | ✓ | TommyHilfiger, CalvinKlein, HeritageBrands |
| `www:BrandAxis` | coined | ✓ | Sperry, StrideRite, SweatyBetty, Sebago |
| `abbv:KeyProductPortfolioAxis` | coined | ✓ | Immunology, Oncology, Aesthetics, EyeCare |
| `exas:ServiceOrProductTypeAxis` | coined | ✓ | Screening, PrecisionOncology, COVID19Testing |
| `lpx:ProducttypeAxis` | coined | ✓ | ValueAdd, CommodityProducts |
| `adsk:ContractWithCustomerResearchDevelopmentChannelAxis` | coined | ✓ | Design, Make |
| `blmn:RestaurantConceptAxis` | coined | ✓ (was segment) | OutbackSteakhouse — brand/concept lines, not segments |

### GEOGRAPHY — region / country / state
| Axis | NS | Status | Member examples |
|---|---|---|---|
| `srt:StatementGeographicalAxis` | std | ✓ · used 400 | US, China, EMEA, IL |
| `us-gaap:GeographicDistributionAxis` | std | ✓ · declared | Domestic, Foreign, regions |
| `us-gaap:AirlineDestinationsAxis` | std | ✓ · declared | route geographies |
| `hig:RegionsAxis` | coined | ✓ | NewEngland, Pacific, MiddleAtlantic |
| `lear:RegionReportingInformationByRegionAxis` | coined | ✓ | UnitedStatesAndCanada |
| `midd:RegionReportingInformationByRegionAxis` | coined | ✓ | Asia, EuropeAndMiddleEast, LatinAmerica |
| `pg:GeographicLocationAxis` | coined | ✓ | RU |
| `alk:InvestmentGeographicRegionAxis` | coined | ✓ (weak) | US, NonUs |

### CUSTOMER
| Axis | NS | Status | Member examples |
|---|---|---|---|
| `srt:MajorCustomersAxis` | std | ✓ · used 201 | Walmart, Kroger |
| `dy:CustomerTypeAxis` | coined | ✓ | Telecom, ElectricalGasUtilities |
| `adi:RevenueFromContractWithCustomerEndMarketAxis` | coined | ✓ (was segment) | Industrial, Automotive, Communications, Consumer — end markets |
| `fn:ContractWithCustomerMarketCategoryAxis` | coined | ✓ (was segment) | Datacom, Telecom, Automotive — customer markets |
| `ter:SeriesOfCustomerAxis` | coined | name+domain · **0 members, 0 use** | domain=`SeriesOfCustomer` (dormant shell — no member breakdown ever captured) |

### CHANNEL — sales channel / franchise-vs-company-operated
| Axis | NS | Status | Member examples |
|---|---|---|---|
| `us-gaap:ContractWithCustomerSalesChannelAxis` | std | ✓ · used 6 | Wholesale, DirectToConsumer, ECommerce |
| `us-gaap:FranchisorDisclosureAxis` | std | ✓ · declared | company-operated vs franchised |
| `us-gaap:HealthCareOrganizationRevenueSourcesAxis` | std | ✓ · declared | payor source |
| `us-gaap:ContractWithCustomerBasisOfPricingAxis` | std | ✓ · declared | fixed-price vs cost-plus |
| `mcd:SegmentReportingInformationBySecondarySegmentAxis` | coined | ✓ | ConventionalFranchises, DevelopmentalLicensees |
| `yum:FranchiseeOwnedStoresAxis` | coined | ✓ | FranchiseeOwnedStores |
| `low:StoreTypeAxis` | coined | ✓ (weak) | DealerOwned |
| `aap:NumberOfStoresAxis` | coined | ✓ (weak) | Stores, Branches, Carquest |

### ENTITY — legal entity / ownership / JV / subsidiary
| Axis | NS | Status | Member examples |
|---|---|---|---|
| `dei:LegalEntityAxis` | std | ✓ · used 3206 | (default-entity wrapper + subs)¹ |
| `us-gaap:EquityMethodInvestmentNonconsolidatedInvesteeAxis` | std | ✓ · used 138 | JV investees |
| `srt:ScheduleOfEquityMethodInvestmentEquityMethodInvesteeNameAxis` | std | ✓ · used 106 | equity investees |
| `us-gaap:JointlyOwnedUtilityPlantAxis` | std | ✓ · used 152 | named power plants |
| `us-gaap:IncomeStatementBalanceSheetAndAdditionalDisclosuresByDisposalGroupsIncludingDiscontinuedOperationsAxis` | std | ✓ · used 57 | NIKE Brand, Solar, MENA (disposal groups) |
| `us-gaap:RealEstatePropertiesAxis` | std | ✓ · used 52 | named buildings |
| `srt:OwnershipAxis` | std | ✓ · used 25 | subsidiaries |
| `ppl:ByCompanyAxis` | coined | ✓ · used 363 | PPLElectric, LouisvilleGas, KentuckyUtilities |
| `aes:DebtDefaultBySubsidiaryAxis` | coined | ✓ · used 16 | AESJordan, Maritza |
| `yum:CompanyOwnedStoresAxis` | coined | ✓ (was channel) | KFCRussia, CompanyOwnedStores — ownership entities |
| `fe:BusinessUnitsAxis` | coined | ✓ (was segment) | SignalPeak — a named entity, not a segment |
| `tsco:ConsolidatedStoresAxis` | coined | ✓ (was segment) | Orscheln, Petsense — acquired legal entities/banners |

¹ `dei:LegalEntityAxis` is ~95% the whole-company default wrapper (structural). Only the named-subsidiary rows are real entity slices. ENTITY is the **fuzzy bucket** — both audit runs agree only the **equity-method/JV** part reliably moves earnings; treat the rest as provisional.

**Verification summary (`wf_07c1c51b`, 39 rows):** 32 survived as slices (26 kept their kind + **6 kind-corrected** above), **2 demoted** to non-slice (see §3), 5 name-liars confirmed out. All 7 multi-voted axes agreed with the verdict.

---

## 3. NON-slice axes whose NAME lies (caught by reading members)
Critical — a name-only filter would wrongly admit these. The first 5 are confirmed non-slice; the last 2 were **demoted from the slice list by `wf_07c1c51b`**.

| Axis | Name suggests | Members reveal | Verdict |
|---|---|---|---|
| `eqt:DistributionChannelAxis` | channel | WestTexasIntermediate, XNYM | price benchmarks → **non-slice** |
| `isrg:CostOfSalesProductsAxis` | product | BeforeCapitalization, CapitalizedIntoInventory | cost accounting → **non-slice** |
| `aep:MoneyPoolParticipantbyCompanyTypeAxis` | company | intercompany money-pool | financing → **non-slice** |
| `dks:RevenueFromContractWithCustomerAxis` | customer revenue | GiftCardBreakage, LoyaltyRedemption | revenue-recognition types → **non-slice** |
| `wmb:CustomerAxisAxis` | customer | ExternalCustomer, InternalCustomer | = intersegment → **non-slice** |
| `hum:LongDurationInsuranceProductsAxis` | product | CoinsuranceAgreement | reinsurance arrangement (multi-vote 0/3) → **non-slice** (demoted) |
| `xray:GeographicalBasisAxis` | geography | DestinationOfShipments | measurement *basis*, not a geographic cut → **non-slice** (demoted) |

---

## 4. The elimination guard (confirm **b**)
Members on the segment-family axes that are accounting plumbing, not businesses. Scoped to segment axes only (a global regex over-catches "CorporateDebtSecurities", pension "ReconcilingItems", etc.).

```
HARD-EXCLUDE  → a FROZEN exact-qname allowlist of PURE eliminations (~24, vetted)
                e.g. IntersegmentElimination, ConsolidationEliminations, GeographyEliminations,
                     SubsegmentEliminations, Eliminations
                + LOG every exclusion (reversible, auditable)
PROVISIONAL   → 241 "real-but-unverified": MaterialReconcilingItems, Corporate, AllOther,
                Unallocated, blended "CorporateAndEliminations", raw Intersegment
                → own row, quarantined from cross-company, NEVER deleted
KEEP          → all other segment members (~3,000 real segments)
```
**⚠️ Why hard-exclude must be a vetted LIST, never a regex:** the "conservative" regex still caught **`GlobalPestElimination`** (Ecolab's real pest-control business — "elimination" = killing pests) + `OperatingSegmentsExcludingIntersegmentElimination` (a real aggregate) + `Priortoelimination` (a real gross). ~20% false-positive rate on what was visible. Remove these by hand once; then freeze.

**Self-heal:** any hidden member that later shows real persistent value → auto-demote to provisional. No human.

---

## 5. The 8 axes the standard-only list missed (confirm **c**)
Deterministic split by namespace (100% certain):

```
COINED (5) → route to PROVISIONAL:  ppl:ByCompanyAxis(363) · qdel:BusinessUnitAxis(16)
                                    · aes:DebtDefaultBySubsidiaryAxis(16) · atk:BrandAxis(2) · ppl:RatesTypeAxis(2)
STANDARD (3) → route to CONFIRMED kind:  us-gaap:JointlyOwnedUtilityPlantAxis(152)
                                    · IncomeStatementBalanceSheet…DisposalGroups…(57) · us-gaap:RealEstatePropertiesAxis(52)
```
Caveat: "confirmed *kind*" ≠ "values compare across companies." `RealEstateProperties` / `JointlyOwnedUtilityPlant` values are company-specific — cross-company comparison is a **separate, not-yet-built layer**.

---

## 6. Runtime table + sentinel (how code uses this)
```python
CONFIRMED_AXES = { axis_qname -> kind }       # every SLICE axis in §2 (frozen)
ELIMINATION_QNAMES = { exact pure-elimination member qnames }   # §4 vetted list

def classify(axis, member):
    kind = CONFIRMED_AXES.get(axis)
    if kind is None:                       return provisional(axis, member)   # SENTINEL: unknown axis, never drop
    if member.qname in ELIMINATION_QNAMES: return hide(member) if not value_is_real(member) else real(kind, member)
    return real_or_provisional(kind, member)
# never DELETE/MERGE by guess; unknown + unsure → provisional (over-split-safe)
```
The sentinel is what makes the residual (§1) safe: a coined slice axis we haven't catalogued surfaces as a flagged provisional row, never a silent merge.

---

## Reproduce
```cypher
-- the operative universe (143 used axes)
MATCH (f:Fact)-[:FACT_DIMENSION]->(d:Dimension) RETURN d.qname AS axis, count(*) AS uses ORDER BY uses DESC;
-- coined slice-name candidates (this sweep)
MATCH (d:Dimension) WHERE NOT split(d.qname,':')[0] IN ['us-gaap','srt','dei','ecd','cyd','us-gaap-supplement','srt-supplement','us-gaap-ebp']
  AND (toLower(d.qname) CONTAINS 'segment' OR ... 'brand' OR 'product' OR 'geograph' OR 'region' OR 'customer' OR 'channel' OR 'division' OR 'businessunit' OR 'subsidiar' OR 'store' ...) RETURN d.qname;
-- members for any axis
MATCH (d:Dimension {qname:$axis})-[:HAS_DOMAIN]->(:Domain)-[:HAS_MEMBER]->(m:Member) RETURN DISTINCT m.label;
```

## Provenance, confidence & changelog

**Snapshot:** 2026-06-26, live Neo4j XBRL graph (read-only, aggregate queries only — per the "never touch Neo4j unless asked" rule, this work was explicitly authorized). The graph grows; re-run the §Reproduce queries on a fresh snapshot before locking.

**How each number was produced (workflow run IDs):**
- `wf_84ed3401` — first full census: classified all 326 standard axes into XBRL-native buckets, 0 residual.
- `wf_8d0398a1` — **lock/completeness audit**: independently re-derived slices over all **143 used axes** (102 std + 41 coined), multi-vote on borderline, 0 residual → the **17 ✓verified** slices + the elimination/`c` findings.
- `wf_07c1c51b` — **swept-rows verification**: adversarial re-judge of the ~34 `~swept` coined slices + the 5 name-liars (this doc's §2 `~swept` rows; results folded in once complete).

**Confidence tiers (the `Status` column in §2):**
- `✓verified` — adversarial-audit confirmed (12 standard + 5 used-coined). Safe to lock.
- `~swept` — name+member sweep classification, adversarially verified by `wf_07c1c51b`. High confidence.
- `(weak)` — borderline (1–2 members or thin signal) → treat as **provisional**, not confirmed.

**Key empirical lessons (so a cold bot doesn't repeat the mistakes):**
1. **`dim_nodes` ≈ 3167 per standard axis is NOT usage** — it's "declared in every filer's taxonomy." Real weight = `FACT_DIMENSION` count. Only 143 of 2,344 axes ever touch a fact.
2. **Classify by MEMBERS, never by axis name** — names lie: `eqt:DistributionChannelAxis` members are WTI/NYMEX *price benchmarks*; `isrg:CostOfSalesProductsAxis` members are cost-capitalization states.
3. **The elimination hard-exclude MUST be a vetted exact-qname list, never a regex** — a "conservative" regex still caught `GlobalPestElimination` (Ecolab's real pest-control business), `OperatingSegmentsExcludingIntersegmentElimination` (a real aggregate) — ~20% false-positive rate. Proven, not hypothetical.
4. **The biggest axis by raw usage is not a slice** — `RevenueRemainingPerformanceObligation…StartDate` (22.9K uses) is a typed *date* axis.

**Status:** ALL rows verified — `wf_07c1c51b` complete: of the 34 swept coined slices, **32 survived** (26 confirmed + 6 kind-corrected: blmn→product, adi/fn→customer, yum:CompanyOwned/fe/tsco→entity), **2 demoted** (hum:LongDurationInsuranceProducts, xray:GeographicalBasis). 2 rows (`rxp:SegmentAxis`→segment, `ter:SeriesOfCustomerAxis`→customer) are **dormant shells** — 0 members + 0 fact-use; kind set from axis name + domain root (`AllSegments` / `SeriesOfCustomer`); member-verification is N/A (no members exist), and the sentinel covers them if ever activated. **So every catalogued row is now resolved — nothing left `~unverified`.** The spec mechanism (`Naming_Slices_XBRL.md`) is final — only this list's contents were pending. Cross-company value comparison remains an unbuilt layer (`Naming_Slices §12`).

