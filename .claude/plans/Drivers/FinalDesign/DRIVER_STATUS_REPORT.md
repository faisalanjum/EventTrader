# Drivers — requirements, implementation, and verified status

**Audit and arithmetic-fix verification date: 2026-09-07. Scope: Drivers only.**

**Reviewed correction commit: `8255d4dc80988ce8490078cbbfa5f7f435817239`**, based on `5f81248e3c1070b8343aa26473865e749ba0d5a0`. The capability assessment is the original main snapshot plus these two arithmetic corrections; it is not a fresh whole-project audit of concurrent recovery-branch work. Working branches must incorporate the correction commit before claiming its results. The tested code tree and exact limits are in section 6.

This is the single maintained handoff from this audit. It replaces the audit's temporary notes, not the owner's governing plans. “Verified” means the stated document, code, test, or graph observation was checked; it does not mean every possible model judgment is correct. Open questions are identified explicitly.

## 1. Read this first

The system should turn source evidence into reusable causes or standing measures, preserve each quoted occurrence, and later connect those facts to explanations of price moves. It must keep different meanings apart, preserve history, and make wrong links reversible.

**Assessment:** the implementation follows much of the intended mechanical foundation, but the complete system is neither built nor proven correct. The two reproduced arithmetic defects D1/D2 are corrected in the reviewed commit; the stale generated-reference test D3 remains open. The semantic reader, identity admission, complete reads, recovery, operations, and production rollout remain substantial work. Good component tests and historical experiment PASS records are not proof of a working end-to-end system.

**Owner decisions confirmed in this conversation:**

- The endpoint is the comprehensive planned Driver system. Fiscal-only is an intermediate milestone; it must not be called full completion.
- Keep the current independent identity-review approach while building the comprehensive version, then optimize with understanding and evidence. One separate AI review can cover all new identity proposals in an event; unchanged, previously approved decisions reuse their frozen approval.
- Audit the actual plans and code independently. LeftOverSteps is a bot's interpretation and must not silently become new law.
- Produce this one detailed handoff and remove only this audit's other files. Preserve existing plans, code, and experiment evidence.
- The later request authorizes isolated investigation, regression tests, and committing/pushing the two arithmetic fixes to main without editing the other bots' working files. This is narrow correction authority, not general Driver activation authority.

**Current production observation:** Driver = 0; DriverUpdate = 0; DriverPeriod = 0. Old Guidance remains: 548 definitions, 8,432 updates, 237 periods. The real Driver adapter refuses transactions; V2 refuses enabled writes. The numerical-fix request does not authorize graph writes, activation, model calls, unrelated implementation, or deleting old Guidance.

**Completion:** 10 of the 31 named, already-defined capability groups below have their component implementation built and tested: **32.3% by this checklist**. Another 8 have partial implementation; 13 have no production implementation. D1/D2 closure moves C05/C08 from partial to built; no other component or production gate was closed by this patch. All 31 are unlaunched as a Driver service. This is a transparent capability count, not an effort estimate. A precise percentage for the owner's entire comprehensive endpoint is unavailable because later channel requirements are not all finalized.

Use this reading order:

1. [Capability status](#2-capability-status--update-this-table-as-work-lands).
2. [Authority and replacements](#3-authority-and-replacement-map--stable-base), then [stable requirements](#4-stable-behavior-a-new-bot-must-preserve).
3. [Code map](#5-actual-implementation-map), [verification](#6-verification-receipt--frozen-september-7-snapshot), [experiments](#7-experiments-results-and-what-they-actually-establish), and [defects](#8-confirmed-defects-bounded-impact-and-closed-suspicions).
4. [Remaining work](#9-does-the-task-list-match-the-intended-scope), [open decisions](#10-named-unresolved-decisions-and-residual-risks), and [maintenance](#11-how-to-maintain-this-one-file).

## 2. Capability status — update this table as work lands

**B** = component built and covered by relevant passing tests; not a claim of production qualification. **P** = partial, experimental, or blocked by a confirmed defect. **M** = production capability missing. **U** = scope not finalized. “Verified” names the evidence or its limit. **Production running: No for every row.** Component utilities can execute without constituting a launched Driver service.

| ID | Required capability | Built | Verified status / exact gap |
|---|---|---|---|
| C01 | Fetch Fiscal sources and group raw V1 submissions by source event | B | Existing fetching, source ordering, packet, sign, and completeness tests; does not supply semantic interpretation. |
| C02 | Build the staged V2 raw event envelope with ordered source parts | B | In-memory Stage-A builder and real-source packet controls; does not activate V2 or turn old packets into new semantic evidence. |
| C03 | Bind supplied facts to the stored source's company, type, and publication time | B | Core input checks and read-only graph tests. Real adapter currently supports Report sources. |
| C04 | Resolve periods and pair earnings 8-Ks through the existing owners | B | Exact date/period fixtures, real pairing controls, and point-in-time checks. |
| C05 | Preserve exact units, scaling, and signs through evidence and fact processing | B | Existing exact conversion plus D1 correction; sign/context/binding tests and complete supported-cache census pass. Storage and parser limits remain explicit. |
| C06 | Build normalized scope and producer-independent fact IDs | B | Fixed vectors, source grammar, measurement/slice folding, canonical decimal and collision signatures. |
| C07 | Fuse compatible fragments and preserve conflicting same-event values | B | Canonicalize-before-fusion, pre-batch collision planning, permutation and late-arrival tests. |
| C08 | Enforce all mechanical fact and lane checks | B | Extensive FACT-16 / shape / surprise tests plus D2 exact movement correction; independent integer/rational controls and both V1/V2 dry-run routes pass. This is not the unbuilt identity-admission kernel. |
| C09 | Bind tagged graph facts to exact printed source evidence and relocate them | P | Detailed namespace/context/unit/dimension/visibility tests, real graph controls, and D1 correction pass. Final Fiscal coverage/reader qualification still remains. |
| C10 | Serve point-in-time slice menus and verify complete fact-level member sets | B | Frozen axis rules, exact company/context matching, no invented union of dimension sets; live read tests. |
| C11 | Plan existing-Driver writes, merges, and failures with truthful audit outcomes | B | Pure writer and injected-store transaction tests; real graph transactions remain fenced. Same-fact member-link enrichment question Q3 is unresolved. |
| C12 | Run the staged V2 conversion and dry-run Core bridge | P | Built with an injected reader, existing-Driver requirement, old three-key reply shape, and writes disabled. |
| C13 | Run the shared production semantic reader with complete item accounting | M | No actual production reader; current experiments are not the recorded August one-item runtime. |
| C14 | Qualify the exact model, prompts, inputs, parser, and scorer for each AI task | P | EXP-0/1/2 have historical signed results; remaining keys and EXP-3/4/5/6 do not have signed PASS. |
| C15 | Admit/reuse/create identities and stamp types/families with a first fact | M | No complete semantic admission kernel or atomic born-complete Driver creation. |
| C16 | Build the offline catalog seed using reusable workflow tools | P | Fetch/chunk/seed/fold/repair/validation tools exist; old rules and unfinished finalization prevent readiness. |
| C17 | Finalize and maintain the catalog across the eligible company population | M | No finalize_catalog.py, complete type/family finalization, qualified whole-population catalog, or live lifecycle/refresh system. |
| C18 | Reconcile synonymous names through one judged link mechanism and frozen anchors | M | SAME_AS judge/application, asynchronous sweep, deferred pairs, and anchor lifecycle are unbuilt. |
| C19 | Apply company-declared continuity with dated, reversible reads | M | No complete ContinuationClaim / CONTINUES_AS admission, judge, or recovery path. |
| C20 | Select and verify company concept links, then persist/recheck them | P | XBRL evidence/member attachment mechanics exist; semantic concept selection, full rollout, and resolution lifecycle do not. |
| C21 | Serve complete raw/reconciled historical series and guidance movement | P | Prior-guidance and member-fold helpers exist; complete public read/collapse/continuity views do not. |
| C22 | Expand explicit guidance withdrawals safely, including late arrivals | M | Full bounded fan-out and read/write integration absent. |
| C23 | Store attribution verdicts and support DailyCompanyMoveEvent | M | No complete verdict writer, channel integration, or daily-move workflow. Some later daily-move rules remain open. |
| C24 | Create graph schema and enable atomic production admission/writes | M | Driver schema/sentinels absent in graph; real writer fenced; setup, approval, and rollback proof remain. |
| C25 | Run the seed gauntlet, contradiction detectors, and calibration/audit lanes | M | Experiment harnesses are not the required running identity safeguards. |
| C26 | Recover wrong links and fact attachments with family propagation and audit history | M | No operational RecoveryEvent machinery or full reversible recovery. |
| C27 | Maintain public receipts, event cursors, retries, and restart-safe operation | M | Internal local write-ahead files are only one component; complete channel-to-Core operating contract absent. |
| C28 | Certify Fiscal on real admitted anchors and independent full-output truth | P | Source/case kits and mechanical tests exist; the real 150-anchor gate and final reader qualification have not run. |
| C29 | Run bounded shadow/pilot, monitoring, backfill, and broader rollout | M | No production Driver population, proven operating cadence, or completed rollout. |
| C30 | Archive old Guidance, migrate consumers, verify restore, and retire it | M | Old graph population remains; no completed archive/cutover/delete sequence demonstrated. |
| C31 | Materialize native XBRL facts under the approved dormant design | P | EXP-1 builds fixture rows; production materializer, reversible lifecycle, convergence, and enablement gates remain. |
| U01 | Finish the comprehensive scope beyond the first Fiscal milestone | U | Later channel charters and several extensions are not final. Excluded from the 31-row denominator, not declared done or discarded. |

Arithmetic: B=10, P=8, M=13; 10/31=32.3% complete components; 18/31=58.1% with some implementation. **Do not interpret partial rows as half-done or these percentages as remaining person-days.** The rows are an explicit audit grouping of obligations, not an owner-signed project weighting. Keep the denominator stable unless a real requirement changes.

## 3. Authority and replacement map — stable base

### 3.1 Which sources govern what

| Source | Authority / proper use |
|---|---|
| [FINAL_DESIGN.md](FINAL_DESIGN.md) | Meaning, identities, facts, naming, units, dates, reads, and concept-link rules. Primary rulebook. |
| [ChannelContract.md](ChannelContract.md) | Active public V1 channel input contract. |
| [15_CandidateFactPacket.md](15_CandidateFactPacket.md) | Active frozen internal V1 packet, with its explicit amendments. Public and internal packets are different boundaries. |
| [BUILD_AND_OPERATIONS.md](BUILD_AND_OPERATIONS.md) | Build/launch gates, writer contract, catalog procedure, retirement, approved-but-unactivated kernel and native-XBRL designs. |
| [STATUS_AND_HISTORY.md](STATUS_AND_HISTORY.md) | Recorded decisions and supersession crosswalk; dated implementation claims must be remeasured. |
| [ChannelContractV2.md](ChannelContractV2.md) | Staged public V2 design. Not active merely because code or a test kit uses V2. |
| [FableExperimentPlan.md](FableExperimentPlan.md), [FableExperimentWorkOrder.md](FableExperimentWorkOrder.md) | Experiment requirements and execution protocol; their approved addenda/pins matter. Signed result artifacts establish experiment status. |
| [Universal Locator Design v5.5](../WIP/UniversalLocator_Design_2026-07-18.md) | Operative Fiscal locator base contract. Its WIP directory does not make this explicitly locked design non-authoritative. |
| [Source-linked/prose FinalPlan](../WIP/UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md) | Current scoped Fiscal amendment/work order. Read over the locator base only for the decisions it explicitly replaces; does not replace Core or general Driver law. |
| [LeftOverSteps/Steps.md](LeftOverSteps/Steps.md) and step0–14 | Execution aid with later recorded “owner rulings.” Separate inherited requirements, proposed implementation detail, and unpropagated amendments. |
| [Fiscal/Core guardrails](../WIP/Fiscal_Core_Review_Guardrails_2026-07-24.md) | Required continuity checklist before Fiscal/Core review, explicitly non-authoritative. Live plans win; old phase status is historical. |
| Archives, old handovers, completed-step reports, Qwen studies | Evidence/history. Not authority to revive a rejected design or activate unfinished work. |

The archived-source crosswalk accounts for 33 source documents, including 27 moved documents and two ratified working-design originals. Use the current consolidated mechanics and explicit corrections; do not reread an old original as a competing live rulebook.

### 3.2 Decisions that must not be revived

| Replaced or limited idea | Final direction / current boundary |
|---|---|
| Catalog-first naming or fitting every item to a displayed vocabulary | Propose the source-grounded name first, then retrieve time-visible evidence cards for semantic reuse. |
| Code parses a prose label into business meaning, using word lists or class guesses | Models propose meaning; code verifies structure, exact source binding, arithmetic, and explicit frozen rules. |
| Bulk creation of all catalog names as empty graph Drivers | Catalog stays offline. Driver and first proven fact are created together, including lazy creation when reusing an offline card. Only admitted-family latent bases may be empty. |
| Old Guidance rows replayed into production Drivers | Archive/QA only; Driver guidance is freshly extracted from source documents. |
| Per-X acronym exception in the August 6 design copy | August 11 spell-out ruling: earnings_per_share, dividend_per_share, etc.; uncertain expansion abstains. |
| Producer/channel identity inside a fact ID | Producer-free source + Driver + scope identity. Producer remains relevant to separate verdicts. |
| “quote_hash” means hash the quote | Historical field name; actual hash is the full ten-slot value signature described below. |
| Guessing unit/scale from names as the future public input | Reader-explicit units and per-slot scale/evidence in staged V2. V1 remains active until the coordinated switch. |
| Raw graph date endpoints directly equal printed inclusive period ends | Reconcile the representation deliberately: graph storage may use exclusive ends; canonical Driver periods preserve their declared date law. |
| Every deterministic locator route is active | Exact tagged-source route is built; unsupported prose/fingerprint routes abstain. Preserve protected legacy known-value behavior until the explicit replacement/caller audit. |
| A tagged evidence packet means native XBRL Driver creation is enabled | Evidence transport is separate. Native creation remains dormant behind P19 and convergence gates. |
| Old multiple-model experiment arms are the plan for new work | Historical results stay intact; later Steps records Sonnet 5 high for still-unrun work. Its policy still needs consistent propagation into older tools/documents. |
| Fiscal release or Step 13 alone means the owner's entire system is complete | Fiscal is a milestone. U01 needs its own finalized scope and closure. |

### 3.3 Later recorded amendments and remaining authority limits

The following are **verified as statements in Steps**, not independently confirmed owner history except where section 1 says so. They are useful evidence of intended direction, but a new bot must not treat this audit as blanket ratification.

- **August 14–15 — identity:** remove stored BROAD and company-count identity/standing/ranking rules; search the whole time-visible catalog; one independent Sonnet 5 high review for every new semantic identity decision, including exact reuse, reorder adoption, creation, and same-meaning links. Batch proposals per event; reuse unchanged frozen decisions. The owner accepted this independent-review approach here. Recovery retains its separately required blind reviews.
- **August 14 — population/lifecycle:** query currently eligible companies and their industry/sector associations; do not freeze historical counts such as 796/786. New-company live admission then catalog refresh; preserve inactive history.
- **August 15 — retries:** only a rule-owned, typed, observable state change may reopen waiting work. SOURCE_UNAVAILABLE has general automatic-retry authority. Elapsed time or vague future evidence is not a sufficient trigger; a genuinely new source event is a new event.
- **August 16 — attribution:** the future attribution channel decides explanatory meaning; Core provides generic validation/storage, not a new attribution brain.
- **August 18 — reader shape:** one already-located raw item plus the full ordered event per call. Code retains exact label/quote/part/occurrence binding. The model emits meaning. Exactly four reply keys: source_id, facts, abstentions, continuity_hints. One or more facts OR one abstention; neither/both is invalid. Malformed reply accepts nothing. Continuity hints are proposals, not facts or an admission bypass.
- **August 18 — one normalizer:** restore code-owned source fields and schema defaults at the existing boundary, then run the complete validators. Do not add a second parser or let the model choose provenance. Raw continuity proposals contain kind/old/new; code attaches provenance. Lower step text asking the model for older provenance fields is superseded by this central statement.
- **August 19 — qualification:** one canonical builder, semantic packet, hidden-key owner, parser/validator, and scorer per AI task. Qualification belongs to the exact model/runtime/configuration/input class. Still-unrun Steps 1–13 use Sonnet 5 high. Step 14 is optional and dormant. The recorded 128,000 output-token setting is a configuration requirement to verify, not proof of present runtime behavior.

**Unpropagated conflict:** BUILD §8.1 and catalog tools still contain BROAD, evidence-mass/standing machinery, company-count retry conditions, and an extra skeptic at ≥8 companies. These are not all compatible with the later recorded count-free policy. Universal independent identity review is confirmed here; the exact remaining eligibility/retry/recovery changes require a narrow rule reconciliation before implementation. Do not silently delete original safeguards or retain contradictory count gates.

## 4. Stable behavior a new bot must preserve

### 4.1 Purpose, boundaries, and graph objects

- **Driver:** one reusable cause, measure, or standing condition, shared across companies/time only when the meaning is the same.
- **DriverUpdate:** one source-backed occurrence. A mention alone is insufficient. The quote remains the precise evidence.
- **Channel:** selects, fetches, and submits raw evidence in publication order per company; keeps outcomes/cursor. It never names/adopts a Driver or writes directly to Neo4j.
- **Shared Core:** interprets evidence, decides identity, validates, and writes. One source event is the submission/fusion boundary, even when a semantic reader processes its items separately.
- **DriverPeriod:** the actual measured/target window, separate from source publication time.
- **SAME_AS:** reversible synonym link. **BASE_METRIC:** type-family link. **CONTINUES_AS:** a company-declared continuity relationship. These have different meanings and gates.
- **EXPLAINED_BY:** optional attribution verdict from an event/move target to a fact. It is not the fact's identity.

    raw source event → shared meaning reader → identity admission
                    → exact validation/write → raw or reconciled historical reads

Missing merges are safer than wrong merges. Facts never move or get re-keyed to hide an identity mistake. Runtime must not depend on a human case queue. Bootstrapping/frozen-rule approval is separate from runtime operation.

### 4.2 Naming, types, and birth

Names carry the reusable cause, not direction, value, date, reporting ticker, measurement version, or the company's own measured business part. An external actor/object causing the outcome stays in the name. Portion qualifiers such as current/funded/fee-earning stay in the name. Standard phrases stay intact; vocabulary is open and source-grounded.

Format is lowercase ASCII letters/digits/underscores, starts with a letter, at least two characters, with no repeated/trailing underscore. Typography normalization is code; plural/stem/acronym meaning is not. Per-X denominators stay in names while values use the base unit. Use explicit spell-outs under the August 11 ruling; no uncertain acronym guessing.

Exactly four permanent types:

| Type | Meaning | Allowed stored states |
|---|---|---|
| metric | A standing numeric or qualitative variable readable again | increased, decreased, unchanged, mixed, reported, persists, unknown |
| guidance | The company's own outlook/target/forecast | introduced, raised, lowered, reaffirmed, withdrawn, unknown |
| surprise | Actual or company guide versus a cross-party expectation | beat, in_line, missed, unknown |
| action_event | A discrete happening | at_risk, announced, occurred, continued, resolved, canceled, suspended, rumored, failed, unknown |

Metric versus action uses the locked persistence question, not a numeric/non-numeric split. DU-05/06 is the locked classifier meaning; DU-07 prohibits invented extra clauses. Bare-root defaults explicitly remain: litigation/convertible_notes/dividend_policy/restructuring_costs = metric; corporate_restructuring/asset_impairment = action.

Admission details:

- Terminal _guidance/_surprise strips exactly one suffix and needs **two independent YES answers** proving the residue is a standing measure and the quote has the relevant outlook/expectation meaning. Stacked suffixes fail. A mid-name occurrence does not count.
- An admitted suffix Driver has exactly one BASE_METRIC to a proven metric. Action has none. Family is not synonymy.
- Bare names run the locked classifier and metric-proof challenge. An evidence-proven metric stamp is required; batch uncertainty falls to action with a counted warning under the specified rule, while live thin evidence parks. A bare name classified as guidance/surprise is a naming error, requiring a proper suffix/re-coin, not that stamp.
- Terminal and type decisions are frozen in their admission memos; refresh/finalize validates the memo instead of rerolling the meaning judgment. No retyping fact-bearing Drivers.
- One real event can justify birth. Driver + first fact are one atomic admission. A bare Driver's first fact cannot have unknown state; a suffix-proven family may start unknown.
- Latent base is the sole empty-node exception: admitted-family proof, valid unsuffixed/non-colliding name, hidden from reuse menus. Graduation requires the exact normalized name and real metric evidence; net_sales cannot fuzzily graduate revenue.
- Offline catalog cards do not grant final identity by spelling alone. An unchanged previously approved decision can be reused; a new decision takes the confirmed independent review.

State meaning belongs to the source: metric direction, surprise favorability, and action stage cannot be inferred from graph history. A bare value is reported; an ongoing condition can persist. For actions, voluntary withdrawal is canceled, involuntary failure is failed, settled dispute is resolved, completed action is occurred; paused is suspended, unconfirmed/denied rumor remains rumored, generic risk boilerplate is not a fact.

### 4.3 Slices, measurement, and exact identity

Slices describe the reporting company's own population. Allowed kinds: segment, product, geography, customer, channel, entity_ownership, unknown. Omit only for actual whole-company scope or no applicable action part; never store slice=total.

- Text uses source evidence and the point-in-time company menu: exact pick, clearly supported new kind/value, or unknown when kind is ambiguous. No near-snap to a convenient menu value.
- Tagged evidence uses the frozen axis/member rules. The current lists contain seven non-slice axes, 12 hard-excluded elimination members, and 79 provisional residual members. The 12/79 counts refer to members, not axes. Other kinds and reversible unknown-axis hex encoding are preserved. Excluded accounting/elimination dimensions refuse the whole fact; never silently turn it into a consolidated total.
- Each supplied dimension needs both axis and member. Empty means verified empty, never failed extraction.
- Member references must prove the full fact-level dimension set in this filing/company/context. None can inherit a proven list; identical lists can fold; different complete lists, including empty versus nonempty, park. Union would invent a context.
- MAPS_TO_MEMBER links a specific DriverUpdate to its verified dimension member and includes axis in edge identity. **This required fact-level linking stays when optional_links is removed.** A fact with no applicable or provable member may remain unlinked; never invent a member just to give every fact a link. Slice-part text is recomputed from the filing label. Member-based grouping is company-scoped; only labels whose linked facts unanimously agree on an exact pair can join. Linkless facts retain their label; history is not rewritten.

Measurement is an open set of exact raw qualifier spans normalized/sorted by code. One maximal contiguous span becomes one token. Empty does not imply GAAP. Source-stated distinctions not otherwise represented must survive; organic/adjusted/constant-currency are not period or growth-basis substitutes.

Fact identity is source event + Driver + ordered scope: period, sorted slice parts, sorted measurement tokens, surprise subtype where applicable, then collision suffix if needed. Producer is excluded. IDs use the existing validated source namespaces and fixed vectors; do not invent escaping or alternative constructors.

The historical **quote_hash** is full SHA-256 over fixed-order compact JSON of canonical strings for these ten slots:

    level_low, level_high, level_unit, change_value, change_unit,
    comparison_low, comparison_high, comparison_baseline, value_text, conditions

Canonicalize units before fusion. Fuse null-compatible fragments first; disagreement in any signature slot prevents fusion. Ambiguous groups park. Then compare against pre-batch graph state: exact merge, compatible fill, conflicting value creates a flagged sibling. Never null-clobber or silently overwrite a conflicting value as a correction. Late arrivals obey the same ladder; at most one bare member per group. Equal-signature race duplicates collapse in reads. Quote/state disagreements have the specified logged deterministic update rule; that does not make semantic identity infallible.

### 4.4 Values, units, shapes, and periods

Store only source-stated numbers. Preserve exact sign/scale. No derived stored growth, ratio, surprise amount, or missing quarter. A net loss is negative; a charge is positive; a benefit/release is negative. Bounds obey algebra, including reversed spoken loss ranges and zero crossings.

Shapes: point has equal low/high; range has ordered bounds; floor/ceiling has one bound; numberless has neither. Transient shape hints are checked then discarded. Guidance alone may carry conditions and numberless value_text; value_text must not coexist with numbers. Company confirmation is derived in Core; the reserved third-party guidance class is not enabled.

Canonical units:

    usd, m_usd, percent, percent_yoy, percent_sequential,
    percent_points, basis_points, count, x, unknown

Reader-explicit V2 units and each slot's value/multiplier/evidence replace inference in the future boundary. Text scale evidence must be local to the quote; verified tagged metadata supplies structural evidence instead. Code multiplies exactly. JSON numbers enter as int/Decimal, never already-rounded float; storage writes exact int64 or a proven float round-trip, otherwise parks NOT_STORABLE.

Growth basis is a source-meaning decision: points/bps wins; YoY/comparable growth is percent_yoy; dated bare growth has the specified YoY convention; sequential needs in-document evidence and is invalid on annual scope. Dateless growth-basis horizons fail closed. Static percentage levels cannot silently become percentage-point changes. Non-USD text money currently uses unknown with monitoring; expanded support needs its governing decision.

Periods are source-backed actual windows, not publication dates. time_type must be supplied at the applicable input boundary, never defaulted. A lawful fully periodless stored fact has no leftover period metadata. Equal-start/end duration is invalid; instant uses the one-day canonical form.

Guidance needs a target period or one explicit permitted sentinel:

    gp_ST, gp_MT, gp_LT, gp_UNDEF

Unresolved dates never become gp_UNDEF automatically. Action periods are optional real windows. Periodless actual surprises are lawful where the full lane rules permit them. Exact ranges, annual, quarter, YTD, TTM, half, monthly, and 52/53-week calendars follow the one shared resolver; no copied quarter matcher.

Earnings 8-K pairing has exactly two owners: the historical exact-accession matcher in the earnings orchestrator's get_quarterly_filings.py, with quarter_identity.py as the AUTO_OK trust check; before the periodic filing exists, quarter_identity.py alone. Current graph ownership and source public time must be read, not trusted from duplicate packet fields.

### 4.5 Surprise, historical reads, and withdrawals

Three surprise scopes: actual_vs_consensus, actual_vs_guidance, guidance_vs_consensus. Basis hint × baseline composes scope before fusion. Guide versus its own previous guide is movement; actual versus prior actual is metric change. Each grounded surprise needs the matching same-event home metric/guidance fact; if absent, park and re-extract the event rather than replaying an orphan alone.

Matching home evidence must agree on family, period/scope, slice, measurement, value, and unit. One event can produce two distinct surprise types. Numberless grounded surprise plus numberless home is lawful. Actual surprise on an unended period fails tense checks.

Code determines polarity-free position, not “higher is better.” Containment or exact closed boundary without favorability wording yields in_line, including a guidance range containing consensus. Outside/open/overlapping cases use the specified source favorability or valid discarded polarity proof; uncertain cases stay unknown. Lower-is-better facts must pass. Offline polarity monitoring reports contradictions; it does not reject all uncommon directions.

Full series key: company, Driver, fact_type, slice, resolved period, period_scope, measurement, exact series_unit, time_type, surprise subtype. Family is added only for cross-flavor views. Unknown units do not absorb known units.

- Point-in-time menus use evidence visible no later than the event. Historical reads use strict date < as_of. This difference is intentional.
- Day is Eastern Time. Same-series/day precedence: 8k > transcript > 10q > 10k > news; then later timestamp, then source ID. Across days latest is current and priors remain history. Amendments are new public-time events.
- Raw and reconciled reads are explicitly labeled; reconciliation is disableable. Member grouping and per-hop continuity cutoffs affect views, not stored IDs.
- Guidance bare values store unknown. Reads derive introduced/raised/lowered/reaffirmed only from safely comparable closed values in the same canonical target series. Missing/open/numberless comparators yield unknown; corrections without business-change evidence do not become raises/lowers. Read-derived effective_driver_state and narrowed are never written back.
- Withdrawal expansion is the single bounded derived write: explicit withdrawal, exact stated scope, currently open and contained guides only. Exclude each guide the same event replaces/reaffirms/keeps, while withdrawing other covered guides. Ambiguous scope does not fan out. Late older covered guides receive missing withdrawal facts additively under the same series lock. Never delete history.

### 4.6 Identity linking, continuity, safeguards, and recovery

The approved kernel is one admission stack: deterministic intake → strong semantic routing/review → attach/adopt/create/park/skip → fact guards. Proposed names are coined before retrieval; retrieval uses time-visible full-catalog evidence. Exact spelling flags a candidate, not proof of sameness. ADOPT is code-verified token reorder only. Born-complete CREATE includes permanent type/family proof and the first fact.

One link mechanism has two triggers: synchronous CLAIM and asynchronous suggestion/sweep. **CLAIM ships OFF** and is shadow-logged; it may enable only after S3. S3 is required even when the launch choice remains OFF; it is not a bot-invented extra gate. Facts stay on their own wording node; links reconcile series additively. No denormalized head_id layer initially.

The link judge defaults to refuse and requires quoted evidence for five checks: same co-extensive object, same population/ownership scope, same causal mechanism, no unresolved rival, and a single-mechanism target anchor. Related, upstream/downstream, correlated, or species/genus meanings are not synonyms.

Permanent refusal classes include cross-flavor, terminal-suffix mismatch, per-X mismatch, and portion supersets. Token-subset species handling is separately OD-19 gated. Named-series distinctions go to the judge, not a curated benchmark dictionary. Flagged/quarantined targets are state-based refusals. Original count-related eligibility/retry details conflict with later Steps and remain Q1.

Birth anchors use raw quoted evidence with frozen hashes, never a model summary. Attached evidence cannot gradually rewrite the definition. Anchor enrichment is default OFF; confirmed bad anchor evidence is redrawn through audited recovery. Variants copy the approved head type and carry provenance/memo/link atomically; facts retain attach_mode and attached_via.

All 14 kernel validators are required: format; link legality; suffix memo; proven single base; suffix/type agreement; latent sanity; collision integrity; atomic admission/type immutability; fact/provenance checks; park integrity; judged deterministic link application; variant integrity; frozen anchors; reversible audited recovery. These are not equivalent to the already-built fact validators.

Seed proof includes static naming/scope/measurement/type-family checks and semantic adjudication of dispersion/gravity/homonym flags; dynamic P1–P9 attacks demand mechanisms, flavor/family, own part versus external cause, measurement, per-X, brand/geography, homonyms, genus/species, and benchmark identity. No wrong convergence is tolerated in the measured gate. Original standing rules need Q1 reconciliation, not guessed replacement thresholds.

Code contradiction detectors raise reversible suspicion; they do not decide business meaning. Planned channels include same-company concept/member splits, same-scope opposing numeric directions, duplicate heads sharing concept evidence, periodicity, qualitative co-occurrence, audit-priority return signatures, and sampled suffix-blind re-derivation. Only their approved subsets are launch-required; optional detector experiments remain gated. Qualitative admission requires its specified non-XBRL duplicate detector; a permanent numeric-only fence would omit planned scope.

Recovery: signal → reversible signal quarantine → two independent strong blind graders on raw evidence (no detector advocacy) → edge quarantine and immutable RecoveryEvent if confirmed. Seed-origin link recovery needs the specified third grader. Still-inconclusive cases stay contained and raise a rule-class question, not an endless owner case queue. Wrong quarantine is reversible at the required bar.

Homonym quarantine propagates to variant/family links for adjudication. Confirmed misattached facts get recovery-only disputed state; affected facts leave history-weighted/cross-company features, not history. Reverting variants park in-flight work; recovery serializes by component. No physical fact replay/re-key/move is a repair.

Calibration streams, blind-grader independence measurement, frozen-key reruns, drift/dispersion probes, false-refusal/duplicate-half-life/park-age metrics, and honest error bounds are part of the required safety evidence. Same-vendor judges are not statistically independent merely because called separately. Qualitative homonyms retain a documented absence of a fully model-independent meaning detector.

### 4.7 Concept links and native XBRL creation

Text-created facts may receive an exact company concept or nothing. Wrong concepts are worse than absent ones. Semantic selection is distinct from proving that a particular tagged graph Fact corresponds to printed evidence.

Text enrichment order: frozen guards → time-visible consolidated numeric company menu → pick one-or-null → exact menu membership → adversarial verify default-refute → deterministic veto → write/abstain. Measurement controls non-GAAP exclusion; guidance/surprise inherit only through a valid BASE_METRIC; action has no direct link. Store xbrl_qname and MAPS_TO_CONCEPT together; a missing graph Concept node must not discard an otherwise valid fact, and reruns can heal linkage.

Frozen G2/G0/G1 guards, unit/time vetoes A–C, and the four-entry component-for-aggregate veto D are explicit design rules, not evidence for a general new word-list system. XC-16 calculation-hierarchy protection and rollout prerequisites must be reconciled at their actual gate; the native materializer explicitly requires it. Original concept model defaults and the later still-unrun Sonnet-only policy are not already aligned in tools.

**Native XBRL materializer: approved working design, dormant.** It creates facts only under already-admitted active company/concept links; it cannot create Drivers. EXP-1's fixture rows do not enable it.

Required native behavior:

- Numeric, non-nil, own-registrant facts in supported fully parsed 10-K/10-Q filings and amendments. Exact context, full dimensions, exact signed values; decimals is precision metadata, not a scale multiplier.
- Unit allowlist USD, shares, USD/shares; count every refused unit/class. Exclude latent bases, unparsed/no-context evidence, unsupported/elimination dimensions. No Q4 derivation, automatic surprise, or guessed fiscal fields.
- Intra-filing precision-aware reconciliation: agreeing rounded duplicates choose highest precision; true conflicts skip with explicit reason. Primary period follows the declared report period; non-primary materialization obeys the new-scope/value-change rule.
- Run native creation before text. Same-head, same-scope compatible text twins defer to native facts within the text's own stated precision; log target ID and crossed synonym edges. Conflicts park by state and may reopen on resolution revocation/link quarantine. Suppression cannot silently lower recall.
- Active/revoked ConceptResolution carries company, Driver, qname, method/model/menu hash/date. Two-grader audited revocation/un-revocation; cohort exclusion at reads; bounded gap repair from the actual skip log.
- Reverse-order compatible text→native upgrade needs immutable UpgradeEvent with complete prior payload and a lossless graded reversal. Incompatible upgrade parks native evidence and preserves the fact.
- Scope/period twin-suspect detector reports exactly one differing component; measurement difference is excluded. It must not snap scope or rewrite IDs. Read-time fold-equivalent twins converge without physical merge.
- Native origin/state/read precedence and empty-measurement≡GAAP folding activate only with their rider. Native reported→effective movement uses the separately specified comparator; never write the derived state.
- P1–P17 and P19 apply; **there is no P18**. X-XL proof gates, a fresh graph census, point-in-time menus, isolated falsifier checks, full concept run, EXP-6 text/native convergence, and industry-by-industry rollout are required before enablement.

### 4.8 Verdicts, retirement, and not-yet-final scope

Verdict fields: explained target Event/DailyCompanyMoveEvent; impact long/short; independent weightage 0.1–1.0 deciles or null; confidence 0–100 in tens; produced_mode live/backfill; producer. Weights are not stored causal shares. Judgment hash is the first 16 SHA-256 characters of impact|weightage|confidence. Read-derived normalized shares may describe a producer's verdict set; grades concern aggregate move/ranking, not invented per-Driver true causal contribution.

Realized returns remain in the price graph and never reach a fact/verdict producer. DailyCompanyMoveEvent ID is dcm:<cik>:<trade_date>, with FOR_COMPANY/ON_DATE. A filing event on that trade day wins at read/grading; preserve an ignored daily-move node and its news verdict, with monitoring. Significance threshold, pure-macro source, and two-independent-catalyst handling remain open.

Retire Guidance only through verified restorable archive → consumer migration/QA → separately authorized deletion. Old rows are QA evidence, never the production seed. NewsChannel, ReasoningTraceQuestions, archived Genesis charters, and Bayes proposal do not provide fully ratified later-channel or learner requirements. Full owner scope must eventually address those needed channels and relevant extensions without inventing their design now.

## 5. Actual implementation map

**Coverage clarification, rechecked September 7:** the current driver/ folder has 29 non-test production Python modules excluding package initializers: 20 Core, five Fiscal, three relocation, and one shared XML-name helper. All 29 are named below. This report explains and points to the code; it does not embed its full contents. Related scripts, catalog tools, tests, and experiments are covered separately. Historical experimental code is not claimed exhaustively verified.

“Evidence-validation complexity” means the checks needed to prove that a number belongs to the quoted source, the right company, the right period, and the stated unit/scope. Without those checks, a real number can still become a false fact—for example, this year's revenue attached to last year's period. This does not mean every current helper or line is necessary; safe simplification must preserve those checks.

### 5.1 Core entry points and the disabled production boundary

| Code | What is actually there |
|---|---|
| [driver_write_cli.py](../../../../driver/core/driver_write_cli.py) | run_event dispatches V1 versus staged V2. V1 loads prepared facts, reads source/typed Driver, resolves/normalizes, fuses, validates, plans, and journals. The V2 route is in the same file from line 930 onward. |
| [prepared_fact.py](../../../../driver/core/prepared_fact.py), [prepared_fact_v2.py](../../../../driver/core/prepared_fact_v2.py) | Strict internal records and unknown-field rejection. V2 conversion is not a public-contract activation. |
| [driver_ids.py](../../../../driver/core/driver_ids.py), [driver_member_fold.py](../../../../driver/core/driver_member_fold.py) | Code-owned identity, exact canonical signatures, measurement/slice normalization and member grouping. |
| [driver_period_resolver.py](../../../../driver/core/driver_period_resolver.py) | Shared date/window resolution, calendar and period invariants. |
| [driver_units.py](../../../../driver/core/driver_units.py), [unit_resolver.py](../../../../driver/core/unit_resolver.py), [slot_convert.py](../../../../driver/core/slot_convert.py) | Active V1 unit support and explicit V2 exact slot conversion. Existing V1 hint behavior is not authority to reintroduce it into V2. |
| [driver_fusion.py](../../../../driver/core/driver_fusion.py), [driver_writer.py](../../../../driver/core/driver_writer.py) | Canonical fragment fusion, immutable pre-batch group planning, late conflicts, exact storage gate, create/merge/fill operations. This writer handles facts for an already typed Driver; it is not the semantic birth kernel. |
| [driver_validators.py](../../../../driver/core/driver_validators.py) | Mechanical fact, type/state, shape, comparison, period, and surprise checks. D2 is corrected here. These are not all kernel V1–V14 admission validators. |
| [driver_neo4j_adapter.py](../../../../driver/core/driver_neo4j_adapter.py) | Real read adapter, source/company proof, periods, prior-guide units, concepts, members, and graph-fact rows. transaction() at line 593 always raises; preflight checks rather than creates required schema. |
| [graph_row_contract.py](../../../../driver/core/graph_row_contract.py), [xbrl_attach.py](../../../../driver/core/xbrl_attach.py), [fact_match.py](../../../../driver/core/fact_match.py) | Strict graph-row contracts, event-level tagged-evidence proof, unit/period/dimension checks, and exact value matching. Not the missing AI concept-identity picker. |
| [slice_menu.py](../../../../driver/core/slice_menu.py), [slice_axis_frozen.py](../../../../driver/core/slice_axis_frozen.py) | Time-visible company menus, full axis/member identity, frozen kinds/exclusions, reversible unknown axes. |
| [outcome_codes.py](../../../../driver/core/outcome_codes.py), [backfill_seam.py](../../../../driver/core/backfill_seam.py) | Typed outcomes and a narrow reconfirmed-candidate backfill seam. Recorded semantic answers in a rehearsal do not become new qualified AI decisions. |
| [xml_names.py](../../../../driver/xml_names.py) | Shared XML name/qualified-name grammar, delegated to the XML library. Both Core and relocation use it; valid Unicode/unprefixed names are preserved and malformed names refused. |

Important route facts:

- V2 still requires an injected reader. V2_REPLY_KEYS at line 930 is only source_id/facts/abstentions; continuity_hints from the later four-key design is absent.
- V2 parks a candidate whose Driver does not already exist. It does not create/admit the Driver.
- V2 enable_writes is rejected at lines 1231–1235. The actual adapter CLI loads RunInputV1. Searches found no external production service calling this Driver route.
- A dry run can emit item decisions written/merged as **planned outcomes**. Run status is dry_run; there was no graph write. Do not total those words as stored facts.
- Internal execution has local locking, write-ahead audit, final in-transaction planning with injected stores, non-retried transaction semantics, and failure accounting. It lacks the complete public channel operating layer.
- The stale validate_via_production facade description does not demonstrate a validator bypass: the underlying conversion → fusion → validation route exists. Contract cleanup still belongs to the coordinated V2 work.

### 5.2 Fiscal fetching and the two locator generations

Current channel code is under [driver/channels/fiscal_ai](../../../../driver/channels/fiscal_ai): run_code_tier.py, build_packets.py, public_contract.py, route_a_source.py, fiscal_ai_rules.py.

It fetches real filing evidence, uses the existing earnings pairing owners, preserves ordered source parts, groups event packets, and records skip/park outcomes. Vendor-derived percentage/common-size/plugs are not automatically eligible source facts. Missing/incomplete searches must not be called terminal absence; the source-completeness stamp and allowed reopening triggers matter.

There are **two distinguishable mechanisms**, not one uniform finished locator:

1. **Protected legacy known-value search:** [scripts/driver_seed/locate.py](../../../../scripts/driver_seed/locate.py) and link_lib.py. It searches for the source's printed occurrence of a value already supplied by the vendor, with exact-cell/row-label, sign, scale, period, and complete-member guards. It contains older token/concept helpers. Its thin value-unknown fingerprint adapter now abstains because it cannot prove full identity. Do not call these legacy helpers the final shared semantic reader; do not delete them without the WP1/caller-preservation proof.
2. **Neutral tagged-source relocation:** [driver/relocation/locator.py](../../../../driver/relocation/locator.py), [inline_html.py](../../../../driver/relocation/inline_html.py), [exact_numbers.py](../../../../driver/relocation/exact_numbers.py). Route A binds actual graph Facts to exact inline source elements and requires local wording/scope evidence. Unsupported prose routes abstain. DOM preparation, visible text, exact quote spans, namespace/context/unit/entity/full-dimension proof, and official transforms are deliberate evidence safeguards.

inline_html.py's large size is not by itself evidence of scope creep: it handles actual source/representation correctness. Exact numeric bugs still exist despite that detail. Source-proof checks must not grow into a second semantic rule engine.

The real Stage-A V2 test rebuilds **11 items** from the current compliant CE/ACI source packets without skipping or changing the preserved raw evidence. A wider inventory includes **7 tracked packet artifacts, 136 event-packet occurrences, 743 items**:

| Source replay category in current local inputs | Event-packet occurrences | Items |
|---|---:|---:|
| Complete quote presence in prepared source | 40 | 137 |
| Source cache missing | 47 | 185 |
| At least one quote mismatch in that event packet | 49 | 421 |
| Total | 136 | 743 |

These are artifact occurrences, not necessarily unique events or semantic truth items. The category names are exact test predicates: a quote-mismatch event's item count does not mean every one of its items is wrong. Conversion preserves raw items mechanically; it cannot manufacture missing evidence. Old packets are not a complete V2 runtime certification.

### 5.3 Catalog workflows

[workflows](../workflows) has source fetching, company scope resolution, chunking, seed assembly, folding, duplicate repair, validation, and resume helpers. Tests prove important structure and constraints, not a fully qualified catalog.

Concrete remaining changes:

- finalize_catalog.py is absent; permanent type/family/admission memo finalization is unfinished.
- **optional_links** is an old catalog field with three suggested references: xbrl_concept (an accounting tag), xbrl_member (a tagged business subdivision/dimension), and guidance_ref (an old guidance reference). Folding keeps a shared reference or clears conflicting references and logs them. Current BUILD §4, lines 110–111, explicitly requires deleting class-level XBRL guesses and unused optional_links. Required accounting-tag/member links instead use the company-specific fact enrichment rules; do not recreate the retired guidance_ref field elsewhere. This is distinct from required SAME_AS, BASE_METRIC, MAPS_TO_CONCEPT, and MAPS_TO_MEMBER relationships, which must remain.
- Final recheck: optional_links execution/merge/output remains in fold_catalogs.py; validate_catalog.py has a stale docstring, tests exercise the old shape, and an old WIP card generator mentions it in a comment. No active production consumer of these suggested references was found. Removal is explicitly specified cleanup, not a new design choice; update the fold machinery and affected fixtures together while preserving historical evidence.
- catalog_first.js is explicitly old/rebuild-pending, not a current production naming path.
- repair_duplicates.js and validate_catalog.py retain ≥8-company extra-review behavior. Later universal-review/count-free direction is not propagated.
- Older model aliases and model-performed mechanical clerk work remain in workflow scripts; they are not ready for the later recorded still-unrun Sonnet-only/code-owned-mechanics policy.
- Full eligible-company query/lifecycle, completed catalog qualification, refresh, protected live-node handling, and seed fitness proof remain.

Checked possible leakage: source fetching carries daily_stock/high_signal metadata, but chunk_company_sources.py uses an explicit six-field whitelist excluding both, and the reader receives that chunk. **No realized-return leak through that reviewed path was demonstrated.**

Review depth: critical runtime paths, rule-owning functions, failure outcomes, and their tests were traced. The complete Core/relocation mechanisms were read in detail; catalog Python flows and relevant JavaScript prompts/rule boundaries were inspected. This is not a claim of exhaustive formal verification of every historical experiment script or JavaScript branch.

### 5.4 Can existing work go straight into production?

**Partly; there is no verified blanket guarantee of only minimal changes.** Reuse the existing mechanical foundation. Step 1 establishes evidence about model behavior; finishing it does not itself deliver the production reader or identity system.

| Existing work | Reuse boundary and remaining work |
|---|---|
| Core, Fiscal, and relocation modules mapped above | These already live outside the experiments and should remain the shared owners of source binding, number handling, periods, IDs, fusion, validation, and fact-write planning. Incorporate the reviewed D1/D2 commit into the implementation branch and connect the missing production components. Reusability does not establish end-to-end readiness. |
| EXP-5 prompt/schema machinery | Some machinery already reads field definitions from Core. The current builder also reads experiment-package Markdown, and the current Core reply shape lacks the later fourth field. The qualified reader machinery needs its ownership moved into Core and its final shape verified; it cannot simply be imported from the experiment directory at runtime. |
| Experiment launchers, hidden answer keys, scorers, replay stores, and fixtures | Retain as qualification/regression tools. They are useful without becoming runtime code. For example, score_exp5.py already calls the actual Core run_event with writes disabled, so that replay exercises shared production-path rules. |
| Catalog and native-XBRL prototypes | Some logic is reusable, but current-plan changes and missing lifecycle behavior remain. The EXP-1 materializer uses float/round arithmetic and an approximate period classifier; its own notes identify throwaway scaffolding and unimplemented cross-event behavior. Its PASS is not permission to deploy that implementation. |

Evidence: [Step 1 purpose and temporary-tool limits](LeftOverSteps/step1.md), [Step 3 smallest design and prompt ownership](LeftOverSteps/step3.md), [current prompt builder](../experiments/harness/build_exp5_contract.py), [real-route replay](../experiments/harness/scorers/score_exp5.py), and [fixture materializer](../experiments/harness/xbrl_dryrun_materializer.py). Step 3 explicitly requires moving the reusable reader owner into driver/core/, proving equivalence to the qualified inputs/replies, and redirecting experiments to that owner. Production must not import experiment tools. This is the recorded execution approach, not a claim that the move is already complete or that every historical script deserves promotion.

## 6. Verification receipt — frozen September 7 snapshot

### 6.1 Source and execution controls

- Original whole-project audit baseline: **5f81248e3c1070b8343aa26473865e749ba0d5a0**, tree **cd80e3b85238b69ab609519d7e9ea655530a4711**. Its inventory covered 267 Python/JavaScript/Markdown source/test files and 180 AST-indexed Python files, not the entire repository or every result artifact.
- Current correction commit: **8255d4dc80988ce8490078cbbfa5f7f435817239**. Frozen, fully regression-tested code tree: **035d5c131aca3a85f7c568ef1cadec2ab6e4d09a**. Exactly two production files and two new test files changed. A separate documentation commit maintains this report without changing the tested code bytes.
- All fix work used an independent clone, independent index, and private temporary copies of the original main and recovery snapshots. Original main and `/home/faisal/EventMarketDB-driver-recovery` working files/indexes were not used for mutations or test output. The latter was checked at **b3b40297a7156e7950c3d1683edb68395f8d2756** on `recovery/a3-a7-verified`.
- The recovery snapshot accepted the patch cleanly and passed the 563-test focused suite in a private copy. That is compatibility evidence for this patch, not a full audit of that branch or proof about later concurrent edits.
- Original plans were read at their current worktree bytes; pre-existing step1 edits, harness receipts, and untracked WIP/Qwen work were preserved. No graph write, AI call, service activation, or message to another bot was performed.
- The narrow correction request authorizes the main publication. Other working branches must merge or cherry-pick the code commit at a controlled checkpoint. Keep already-frozen experiment receipts tied to their original bytes; re-freeze/requalify affected future results after integration. A main push does not update another bot's working tree automatically.

### 6.2 Tests actually run on the correction

| Suite / condition | Final unique result | Evidence / limit |
|---|---|---|
| Core + relocation + experiment harness, excluding live/live_write | 3,846 pass; 1 fail | Full run: 3,845 pass/2 fail/59 deselected in 701.74 seconds. One check inspects uncommitted production edits and flagged the intentional validator edit. After committing identical code bytes, that check passed; the two-check rerun took 20.42 seconds. D3 still failed. The gate was not edited or weakened. |
| Core/relocation/harness read-only graph lane | 58 pass | 152.04 seconds; no writes. |
| Fiscal top-level tests + catalog workflow tests | 550 pass; 1 skip | 131.02 seconds; 272 Fiscal + 278 catalog. Existing optional live embedding-ranking test not enabled. |
| Live graph numeric write round-trip | Not run | `test_neo4j_numeric_roundtrip.py` writes to Neo4j and remains outside authorization. |

**Combined final unique identities: 4,454 passed; 1 failed; 1 skipped.** The 165 new arithmetic tests are included in that total. Focused, baseline, mutation, and recovery-copy reruns are supporting evidence, not additional unique passes. The original pre-fix audit was 4,289 passed/1 failed/1 skipped.

The remaining failure is D3's stale reference heading. Its exact test also failed on the unchanged original commit in a separate pristine copy (21.50 seconds), with the same expected/actual hashes. Do not call the whole suite green or attribute that existing failure to the numerical changes.

Tests use the repository venv, disabled pytest random-order/cache plugins, and `PYTHONDONTWRITEBYTECODE=1`. Existing source/worklist dependencies were supplied only inside the clone: 33 missing files, 131,561,132 bytes, manifest SHA-256 **bb8215dad3ddaa22e00e107a6a96fa1c2348daa52f33200c55962e2e6cf01358**. This copy required fewer files than the original audit's 37-file fixture supplementation because four were already present. Neo4j configuration contained only URI/username/password in a temporary mode-0600 `.env`; credentials were never printed or committed.

The optional skip is `workflows/tests/test_repair_duplicates.py::test_live_embeddings_rank_semantic_pair`, controlled by `RUN_LIVE_EMBEDDINGS`. Existing helpers produced unclosed-Neo4j-driver warnings; the harness also emitted existing unregistered `llm` marker warnings. Neither warning was silently converted into a passing production-readiness claim.

### 6.3 Read-only graph census

Measured at **2026-09-07 11:29:14 UTC**, with key counts rechecked later that day:

| Labels | Count |
|---|---:|
| Driver / DriverUpdate / DriverPeriod | 0 / 0 / 0 |
| Guidance / GuidanceUpdate / GuidancePeriod | 548 / 8,432 / 237 |
| ConceptResolution / ContinuationClaim / RecoveryEvent / UpgradeEvent / DailyCompanyMoveEvent | 0 each |

No Driver constraints/indexes or four sentinel periods were returned. Old Guidance retains three uniqueness constraints and five relevant online indexes. Explicit scalar count queries were used so zero-count labels could not disappear from a grouped result.

Reproducible read-only queries:

    MATCH (n:Driver) RETURN count(n) AS count
    MATCH (n:DriverUpdate) RETURN count(n) AS count
    MATCH (n:DriverPeriod) RETURN count(n) AS count
    MATCH (n:Guidance) RETURN count(n) AS count
    MATCH (n:GuidanceUpdate) RETURN count(n) AS count
    MATCH (n:GuidancePeriod) RETURN count(n) AS count

Repeat that scalar pattern for the five lifecycle/event labels above. Schema checks:

    SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties
    WHERE any(x IN labelsOrTypes WHERE x IN $labels)
    RETURN name, type, labelsOrTypes, properties

    SHOW INDEXES YIELD name, state, type, labelsOrTypes, properties
    WHERE any(x IN labelsOrTypes WHERE x IN $labels)
    RETURN name, state, type, labelsOrTypes, properties

    MATCH (p:DriverPeriod)
    WHERE p.id IN ['gp_ST','gp_MT','gp_LT','gp_UNDEF']
    RETURN properties(p)

The data-dependent precision census and its important limits are in D1. No judgment about existing Driver corruption is inferred from tests with fake Drivers; the real graph has none.

### 6.4 Arithmetic class audit and limits

The affected inventory was derived from the actual functions, conditional expressions, failure branches, exceptions, callers, changed files, and graph/cache populations. New durable tests live in [test_exact_sign.py](../../../../driver/relocation/test_exact_sign.py) and [test_exact_movement.py](../../../../driver/core/test_exact_movement.py). Existing tests remain the owners of unchanged source, unit, shape, period, transaction, and identity rules.

| Rule boundary / input class | Independent proof and result |
|---|---|
| `printed_value`: sign after declared/no transform | 4 precisions × all 8 Decimal rounding modes × 2 format modes; absent/empty/negative signs, 29/80-digit coefficients, tiny fractions, trailing zeros, signed zero. Expected values come from exact decimal strings/tuples, not the production sign operation. |
| `reconcile` → `bind_graph_fact` → `Locator.locate` | Exact and one-digit-wrong controls for both signs, 7 coefficient widths, scales 0/6, 3 precisions; original rounding collision and full locator output tested. Wrong values refuse; exact values survive. |
| Transform/parse/scale refusals, entity/unit/period/dimension bindings | Existing `test_transform_registry`, `test_bind_graph_fact`, `test_route_a`, `test_two_view_bridge`, and exact-number suites passed in the broad regression. Invalid sign/no-format values and fixed-zero controls are also in the new tests. Unknown transforms and genuinely unrepresentable evidence retain their existing refusal boundary. |
| `_num_error` → `validate_fact` → `_movement` | 15 point/range/carry/cancellation/int64-boundary cases × all 16 int/Decimal endpoint combinations × 4 precisions × 8 rounding modes × all 3 states = 23,040 decisions. Integer arithmetic independently supplies expected order. |
| Mixed decimal exponents and comparison order | 1,001 deterministic mixed-exponent cases, all 3 states, precisions 1–50, all rounding modes and clamp 0/1; `Fraction` is the independent test oracle only. Common-exponent cases span −4093 to +4094 and reverse current/prior. Compact `2e5000` and zero exponent ±5000 cases pass. |
| Zero, malformed numbers, missing bounds, skips, wrong range direction | Every numeric field tested with bool/float/string/NaN/sNaN/infinities and a valid positive control. Missing/open bounds still skip midpoint inference; unknown state is not invented; reversed ranges still reject. Zero normalization survives a strict rounding trap. |
| Caller context and traps | Narrow exponent settings, Inexact/Rounded/Overflow/Underflow/Subnormal traps (plus FloatOperation for movement), and context flags are checked. Fixes preserve caller settings, flags, and fact dictionaries. |
| Reachable V1 and staged V2 event paths | Both actual `run_event` routes execute with injected readers/stores, precision 6 and default 28, correct raised and wrong reaffirmed controls. Correct result is accepted into the dry-run plan; wrong movement rejects; stores receive zero writes. |
| Finite observed source/data populations | All 12,402,201 numeric non-nil graph Facts counted read-only; all 1,769 cached `.htm` sources scanned. Accepted, nil, unsupported, parse-refused, and changed-zero categories are reported in D1. No existing DriverUpdate population exists to test production guidance on. |
| Production activation, AI meaning, resource extremes | Unchanged and unqualified by this patch. Real numeric writes were not run; no semantic reader/admission qualification is implied. Arbitrarily large exponent spans, memory exhaustion, and values beyond the Decimal arithmetic implementation's limits are not guaranteed. The existing 4,096-character canonical-number limit in `slot_convert` is unchanged. |

**Failure-first evidence:** before either correction, the initial test set produced 103 failures/55 passes. The final 165-test set against both original production files produced **108 failures/57 passes**. It passes with the corrections. This includes regressions through the actual event/binding doors, not only helper assertions.

**Mutation evidence:** restoring original behavior or breaking each required piece caused test failures. Ten additional deliberate mutations failed as follows: lost negative sign 73; all signs made negative 71; fixed precision 33; missing carry digit 32; missing exponent-span allowance 4; missing zero normalization 1; inherited exponent limits 32; raised accepts equality 39; lowered accepts equality 39; reaffirmed accepts difference 49. Every mutation was restored inside the isolated clone; none reached the committed candidate.

**Direct execution trace:** the 563-test focused set covered statement starts as follows: `_num_error` 8/8, `_movement` 17/17, `validate_fact` 75/77, `printed_value` 18/22, `reconcile` 9/11, `bind_graph_fact` 66/69. This is a narrow line trace, not 100% branch coverage. Its unhit statements were unchanged source-type/decrease-sign refusals (263/294), transform refusal/output guards (3636/3654/3660/3663), failed-base/ExactError reconciliation exits (3972/3982), and entity/duration/format refusal exits (4208/4284/4387). They remain mapped to the broader existing owner suites; an assertion of complete executed-branch coverage would be unsupported.

**Conclusion supported by the evidence:** the original errors violate existing rules, and the narrow corrections pass the specified arithmetic classes, relevant full regressions except D3, and an isolated recovery-branch integration check. This is strong bounded verification, not an absolute guarantee over every future input, dependency change, branch integration, or model interpretation.

## 7. Experiments: results and what they actually establish

### 7.1 Signed experiments

| Experiment | Signed status | Checked conclusion / limit |
|---|---|---|
| EXP-0 — grader qualification | PASS, July 10 | 160 planted pairs; two independent Sonnet 5 high graders qualified under the historical protocol, Opus backup. Not universal identity correctness. |
| EXP-1 — deterministic XBRL reality | PASS, July 9 | 9,603 fixture materializations and independent historical source comparison report. Not production Driver admission or current native-XBRL readiness. |
| EXP-2 — reader configuration | PASS, July 11 | Sonnet 5 high, one 40k run selected on relative quality/cost gates. Recall was 40.43%, sampled precision 85%; PASS never meant exhaustive extraction. |
| EXP-3 — retrieval/router | No signed PASS found | Frozen/qualified remaining inputs and execution required. |
| EXP-4 — identity/type/family | No signed PASS found | K-pairs.v2/K-stamp work and admission evidence remain. |
| EXP-5 — full semantic fact fields | No signed PASS found | K-fields not frozen/qualified; later runtime shape unimplemented. |
| EXP-6 — text/native convergence | No signed PASS found | Depends on the corresponding real components and native gates. |

The ra_0007 judge-contract carry-forward must be resolved before drafting/adjudicating K-pairs.v2. K-route/K-stamp and other remaining keys are not completed by having an experiment harness. Thirty-six event source packets and a proof kit are useful assets, not all semantic keys or gates.

**Step 1 percentage boundary:** its publication plan names six final packages: K-fields; the mini-catalog/K-stamp/EXP-4B freeze; EXP-4A; EXP-3; EXP-5; and EXP-6. At this snapshot, **0 of 6 are fully complete**, although supporting tools, source inputs, and partial work exist. Step 1 explicitly lists EXP-0/1/2 and the older kit construction as already-completed starting assets; counting their three historical PASS results out of seven experiments would not measure completion of the remaining Step 1 work. A code-built or effort-weighted percentage has not been established. Among Steps 1–13, Step 1 is **1/13 = 7.69% by step count only**; the steps are unequal and this is not its measured share of total work. Do not mix these denominators with the separate 31-capability system checklist in section 2.

### 7.2 EXP-0 arithmetic and provenance

Primary preserved record: [EXP-0 v1.3 composite](../experiments/exp0_graders/runs/2026-07-10T00-10-11Z_exp0v13composite/decision.json).

K-pairs.v1.3 contains 160 unique pairs: **110 DIFFERENT, 50 SAME**. Independent raw-output parsing verified exact key coverage and recomputed:

| Arm | Wrong SAME | False refusal | Invalid |
|---|---:|---:|---:|
| Sonnet A | 0 | 0 | 0 |
| Sonnet B | 0 | 1 | 0 |
| Opus | 0 | 0 | 0 |

The composite reuses 159 unchanged v1.2 pairs per arm and contains one fresh kp_0022 result per arm: 477 reused and three fresh pair-arm results. Initial/v1.2 FAIL records remain preserved. kp_0022 had a documented source-key correction; this is not 480 newly collected v1.3 calls.

Zero wrong links on 110 DIFFERENT controls gives a rough rule-of-three upper bound of 2.73% for that sampled class, not zero error on unseen meanings. A generic duplicate-ID weakness in dict-based scoring did not conceal an actual duplicate/coverage problem in these artifacts; this audit independently checked identities.

### 7.3 EXP-1 scope

Primary preserved record: [EXP-1 run](../experiments/exp1_xbrl/runs/2026-07-09T14-25-39Z_dryrun/decision.json).

Recounted materialized.jsonl: **9,603 rows and unique IDs**. Units: 9,098 m_usd, 297 count, 208 usd. Period scopes: annual 2,330; exact_range 972; null 1,733; quarter 2,810; ytd 1,758. Actual file hash matches the saved repeat-run hashes.

The saved XXL0 verifier reports 67,221 field comparisons, seven per row, zero mismatch. **This audit verified the report and row/hash arithmetic; it did not rerun all 67,221 original graph comparisons.** Driver/resolution IDs are fixture identities, not real semantic admissions. The historical materializer used older float/rounded money handling and then-current period conventions. Its result must not be promoted to proof of current V2 exact decimals or the later dormant rider. The historical dual-CIK skip cohort and absent categories remain declared limits.

### 7.4 EXP-2 independent recomputation

Primary preserved record: [EXP-2 decision](../experiments/exp2_reader/runs/2026-07-11T19-40-47Z_exp2/decision.json) and [scores](../experiments/exp2_reader/runs/2026-07-11T19-40-47Z_exp2/scores.json).

The frozen K-reader.v3 has 1,175 keys. Recomputed recall over saved semantic grades and precision over each arm's 60-item sample:

| Arm | Recalled / 1,175 | Recall | Valid / 60 | Sample precision |
|---|---:|---:|---:|---:|
| Haiku, 40k, one run | 364 | 30.98% | 49 | 81.67% |
| Sonnet, 40k, one run — selected | 475 | 40.43% | 51 | 85.00% |
| Opus, 40k, one run | 498 | 42.38% | 53 | 88.33% |
| Cheap paragraph arm | 567 | 48.26% | 51 | 85.00% |
| Opus paragraph arm | 603 | 51.32% | 56 | 93.33% |
| Cheap two-run union | 501 | 42.64% | 51 | 85.00% |
| Cheap three-run union | 571 | 48.60% | 47 | 78.33% |
| Rules-ablated arm | 675 | 57.45% | 11 | 18.33% |

All saved reported metrics match independent arithmetic. The audit collapsed **1,618 identical repeated grade entries with zero contradictory repeats**, then verified every arm's complete key coverage. This was not a fresh blind semantic regrade.

Why PASS selected Sonnet: its recall gap to Opus was 23/1,175 = 1.957 percentage points, inside the relative gate; sampled precision differences were within the recorded uncertainty. Paragraph chunking cost materially more; the two-run union missed its gain threshold; the three-run union failed its new-junk gate; dropping rules traded quality for apparent recall. These are configuration tradeoffs, not proof that 40% recall fulfills the eventual product.

Original score_exp2.py contains machine-specific Windows paths and double-loads stage-1 grades. The signed scores normalize the denominator to 1,175, and the independently recalculated ratios are correct. Do not claim the published recall is invalid; do not claim the raw old script alone portably recreates the complete signed result.

### 7.5 Later failed K-fields work

[BUDGET.json](../experiments/BUDGET.json) currently records **3,070 total calls, 2,900 strong-model calls**. Nine August 16–18 failed-work rows total **140 calls**: 10 + 2 + 2 + 2 + 11 + 7 + 30 + 5 + 71. These are ledger/document-verified counts, not an independent audit of provider billing/service logs.

The last discovery run, kf-discovery-20260818T213000Z, records 72 scheduled identities, 71 answer-bearing calls, and one pre-answer service refusal. Thirty-five valid replies located 2,013 items; 36 invalid replies comprised 17 ambiguous repeated quotes, 17 absent quotes, and two cross-part quotes. Its 37-item retry set exceeded the remaining 28-call allowance, so no retry was run. Those outputs are failed discovery evidence, not a frozen truth key.

step1.md already recognizes reconstructed totals of 3,070/2,900, but still describes the “published ledger” as 2,930/2,760 and asks to reconcile it; the actual ledger now contains the larger totals. Preserve the failures, distinguish historical baseline from current usage, and verify any independent review before the next call. Do not add the 140 again.

The later one-item benchmark/controls and recorded 196-prompt expectation do not have a verified frozen final packet/path/hash in this audit. Do not report them built or rerun failed calls as though they were untouched holdouts. The original proof-kit manifest is historical infrastructure, not completed K-fields.

### 7.6 Qwen status

[LeftOverSteps/QwenInference.md](LeftOverSteps/QwenInference.md), dated August 20, is the most recent local Qwen status ledger. Earlier READMEs are snapshots.

- No production Driver role is approved or wired. The trigger requiring a frozen K-fields key and Sonnet baseline has not fired.
- Table evidence is development work: an opened 93-case set went from per-cell failure to 93/93 in later choice/compact-row forms; qf01 has 19/19. Reworking already-opened cases is not unseen qualification.
- Independent strict parsing of the 160 saved identity replies against the original planted key yields **157 correct, 0 wrong SAME, 2 false refusals, 1 invalid**. This matches the recorded counts; it does not meet a universal “100% correct” claim.
- The 10-of-40 reader-chunk exercise uses a name-or-quote-hit proxy near 50%, not full independent semantic grading.
- The client has no demonstrated true pre-call token cap, and the pending 196-prompt comparison is not verified frozen. Do not turn Qwen into a Step-1 replacement or add a provider framework.

**When to compare a local model:** QwenInference.md's “immediately after A4” wording is conditional on both a locked answer key and a locked Sonnet baseline. Step 1 A4 locks K-fields; A7 runs and scores the EXP-5 reader baseline. A4 alone therefore does not establish readiness for that comparison. An isolated reader comparison after A7 passes is a reasonable early diagnostic recommendation, using the same frozen task, independently established hidden answers, code checks, and scoring; it proves no other AI role. Routing, identity, and type decisions need their own relevant baselines. The current Steps policy still reserves Steps 1–13 for Sonnet and places optional cheaper-model qualification/promotion in Step 14 after Step 13. An earlier local-model experiment would require a narrow owner amendment; this timing recommendation does not grant it, launch a call, or approve a replacement. Any later runtime/prompt/task change invalidates the affected earlier qualification until rechecked.

## 8. Confirmed defects, bounded impact, and closed suspicions

**Meaning of “full reproductions”:** the runnable examples below show the exact inputs, required result, actual wrong result, and code location so another bot can reproduce the error without rediscovering it.

**Correction status:** D1/D2 are fixed in **8255d4dc80988ce8490078cbbfa5f7f435817239**, with the full evidence and exclusions in section 6. The snippets below preserve the independently reproduced **pre-fix** behavior; on the corrected commit their outcomes match the required column. There is no unresolved specification question about retaining exact signed values or comparing guidance midpoints correctly.

Both original defects were reproduced on main `5f81248e` and recovery `b3b40297`; their affected source files were identical. The correction was developed/tested in an independent clone and applied/tested in a private copy of the recovery branch. This does not alter another bot's working files or certify later branch edits. Integrate the code commit at a safe checkpoint and keep experiment receipts tied to the bytes they actually used.

### D1 — signed inline numbers can round before exact reconciliation

**Corrected D1.** Owner: [inline_html.py](../../../../driver/relocation/inline_html.py), printed_value(), line 3669:

    return -value if sign == '-' else value

The original expression above is replaced by `return value.copy_negate() if sign == '-' else value`. Decimal unary minus uses ambient precision. At the default precision 28, a longer exact coefficient can round. The existing 29-digit positive-scale test and small negative-sign test miss their intersection.

**Explicit rule:** the Source-linked/prose FinalPlan §5A step 4 (line 143) requires exact reconciliation of displayed text, format, scale, sign, and graph value; the locked locator base repeats the exact-equality requirement. The defect violates this existing arithmetic rule and does not call for a new semantic check.

Independent exact expectation is coefficient-preserving negation, not running the same arithmetic twice. Reproduction through the **full existing bind_graph_fact fixture**, not only a helper:

    # Run with venv/bin/python from the repository root; read-only, no graph I/O.
    from decimal import localcontext
    from driver.relocation.test_bind_graph_fact import (
        _doc, _bind, D29, D29_RAW, D29_RAW_WRONG
    )
    with localcontext() as ctx:
        ctx.prec = 28
        for sign in ("", "-"):
            for label, raw in (("exact", D29_RAW),
                               ("rounded_wrong", D29_RAW_WRONG)):
                bound, why = _bind(_doc(shown=D29, sign=sign),
                                   raw_value=sign + raw)
                print(sign or "+", label, bound is not None, why)

Fixture display: 10000000000000000000000000001, scale 6. It uses the existing integer graph-formatting fixture rather than a fractional value the upstream formatter cannot produce.

| Input | Required / corrected result | Pre-fix actual |
|---|---|---|
| Positive exact graph value | Accept | Accept |
| Positive rounded-wrong graph value | Refuse | Refuse |
| Negative exact graph value | Accept | **Refuse: value_does_not_reconcile** |
| Negative rounded-wrong graph value | Refuse | **Accept** |

Broader direct reconciliation probe: 48 cases across precisions 6/28/50, digit lengths below/at/above precision, official/no transform, and both signs. **36 exact, 12 rounded; all 12 rounded cases accepted the corresponding rounded-wrong graph value.** Positive controls and exact coefficient negation supplied independent expectations.

Population checks (repeated against the correction on September 7):

- At **2026-09-07 16:18:41 UTC**, all 12,402,201 numeric non-nil graph Facts were counted again; 1,256,549 were negative. None of their stored negative strings had more than 28 digit characters; maximum was 14.
- That graph observation alone cannot exclude impact: a rounded short graph string could conceal a longer printed source number.
- Therefore all **1,769 current cached .htm sources** were scanned again at **16:21:29 UTC**. 1,768 parsed as XML; one refused with XMLSyntaxError (0001579241-25-000008.htm). Of **254,204 negative inline numeric tags**, 254,195 yielded exact negation, four were refused nil values, and five were unsupported/non-numeric transforms. **Zero changed numeric values in the parsed, supported cached population.** The correction changed the Decimal sign representation of 1,770 zeros; numeric equality was unchanged. Eight signed/trailing-zero controls through slot conversion, identity canonicalization, and `storable` all produced the same canonical/stored zero.
- This is not a scan of uncached source documents. It does not certify arbitrary precision settings or every possible future filing.

Read-only numeric census query:

    MATCH (f:Fact)
    WHERE f.is_numeric='1' AND f.is_nil='0'
    WITH f, replace(replace(replace(f.value,',',''),'-',''),'.','') AS digits
    RETURN count(f) AS numeric_non_nil,
      sum(CASE WHEN f.value STARTS WITH '-' THEN 1 ELSE 0 END) AS negative,
      sum(CASE WHEN f.value STARTS WITH '-' AND size(digits)>28
               THEN 1 ELSE 0 END) AS long_negative,
      max(CASE WHEN f.value STARTS WITH '-' THEN size(digits) ELSE 0 END)
        AS max_negative_digits

The correction census used lxml with external entity/network resolution disabled, ix:nonFraction sign='-', the existing `fact_value_input`/`printed_value`, and independent coefficient-tuple sign expectations. No fetching was needed. Current cache-manifest SHA-256: **e02eadcce0ed8f38871ef4ee9b2b859799dc0dab12f3d80bc83f01e6112fac39** (the earlier audit used a different manifest serialization). Transform categories and counts: no format 143,447; 2020 num-dot-decimal 65,091; 2015 numdotdecimal 15,092; 2022 num-dot-decimal 28,846; 2015 zerodash 783; 2022 fixed-zero 75; 2020 fixed-zero 861; SEC numwordsen 5. The last five remain unsupported/non-numeric, and four other tags are nil; neither category is counted as a successful numeric binding.

**Impact:** wrong binding and false rejection are proved for legal structural inputs. Existing Driver corruption is not shown; there are no Driver facts, and the long fixture could also meet a later storage refusal. The correction uses the existing Decimal coefficient-preserving sign operation at this one owner. It adds no source-value restriction, transform implementation, or semantic check.

The original in-memory direction probe is now superseded by the committed correction, durable tests, finite-population comparison, and regression receipt in section 6.

### D2 — guidance midpoint comparison loses integer/Decimal exactness

**Corrected D2.** Owner: [driver_validators.py](../../../../driver/core/driver_validators.py), _movement(), line 477:

    mid, cmid = (lo + hi) / 2, (clo + chi) / 2

The original expression above used Python floating-point division for allowed integer inputs. Two distinct exact midpoints can become equal. Reproduction:

    from driver.core.test_driver_validators import mk, check
    for state in ("raised", "reaffirmed"):
        fact = mk("guidance", "point", driver_state=state,
            level_low=9007199254740993, level_high=9007199254740993,
            comparison_low=9007199254740992,
            comparison_high=9007199254740992,
            comparison_shape_hint="point",
            comparison_baseline="previous_guidance")
        print(state, [v.code for v in check(fact)])

Required and corrected: raised passes, reaffirmed fails. Pre-fix actual: raised fails MOVEMENT, reaffirmed passes. These values fit int64. The same pair supplied as Decimal passes/fails correctly at precision 28.

**Explicit rule:** FINAL_DESIGN §4.3 (line 133) requires midpoint up/down/equal to agree with raised/lowered/reaffirmed. BUILD §11.4 requires exact numeric input; the public validator accepts finite int/Decimal. The writer's own storable() independently accepts both example integers exactly. Therefore this is not an invalid-input example. The stale ≤15-digit validator docstring does not override the actual exact-type rule and writer-owned storage decision.

Whole-boundary probe: eight point/range/equality/negative/below-and-around-2^53 cases × int/Decimal × precisions 6/28/50 × three states = **144 checks**, with Fraction-computed expected state. **112 correct, 32 wrong:** eight wrong integer judgments at each precision and eight Decimal judgments at precision 6. Small positive/negative/equal controls stayed correct.

The pre-fix recheck repeated all 144 checks and obtained the same counts. The slot converter converts integers to Decimal before event validation, so the integer-only example does not by itself prove a current event-route error.

**Correction:** compare exact endpoint sums; dividing both by the same positive 2 cannot change their order. All four finite int/Decimal endpoints are represented exactly as Decimal. In a private context, precision is `max(nonzero.adjusted()) - min(nonzero.exponent) + 2`: align every coefficient and allow one carry digit. Zeros are normalized so an irrelevant zero exponent cannot force rounding. Emax/Emin are widened to the implementation limits, clamp is cleared, and caller context is preserved. No fixed digit threshold or second rule engine is added. The `MOVEMENT`/`REJECT` result is unchanged; its diagnostic now says the stated movement contradicts the midpoint rule without formatting potentially enormous midpoint values.

**Reachability now tested:** new tests execute both actual V1/V2 event routes at precision 6 and default 28 with injected readers/stores. The low-precision cases fail on the original arithmetic and pass with the correction; the default-28 examples remain correct. Integer/Decimal mixtures, negative/range/equality cases, and independent exact rational expectations are covered in section 6.4. These are dry-run proofs. No production guidance corruption was demonstrated, and the real graph still had zero DriverUpdates.

### D3 — stale pin inventory, the one remaining existing-test failure

test_g_suite.py::test_the_pin_inventory_is_REPEATABLE_and_matches_disk (line 1102) fails because regenerated pin inventory has exactly one changed heading row:

    STATUS owner rulings record (through 2026-08-11)
    → STATUS owner rulings record (through 2026-08-12)

Generated inventory SHA-256: cffc94a063c6b82f7fe40a64b2bcddeceaeb183b27ff87208499eeab3331931e.
Committed inventory SHA-256: 7388fca392006c2b2ac8c6097c28969b75364bdfcc9de4b977ed11ed597b626f.

This is a stale index reference, not a changed packet hash or demonstrated production rule failure. Regenerate only after checking the intended heading/source, not as a blind green-test repair.

### Q3 — same-fact member enrichment on replay is not settled by the cited rule

Reproduced through run_event with an injected store: a new fact with verified member refs plans MAPS_TO_MEMBER; the same already-stored, unlinked fact replayed with those refs returns merged and plans **zero operations**. _create emits edges; _merge_or_fill only emits property changes.

FS-18/FS-21 requires fact-level member enrichment but does not explicitly settle retroactive member-edge addition on that identical existing fact. **Verified limitation; not classified as a definite plan violation.** Before fixing, resolve whether rerun enrichment is required and review the whole existing-fact/fill class. Do not add a special branch for this one fixture.

### Closed or narrowed suspicions — do not reopen without new evidence

| Suspicion | Verified resolution |
|---|---|
| Green tests prove end-to-end readiness | False: missing components, disabled writes, zero Drivers, and unrun semantic gates remain even after D1/D2 correction. |
| Missing same-fact member edges are certainly a design violation | Not settled; Q3 above. |
| V2 helper name implies validation is skipped | Underlying conversion/fusion/validation exists; no bypass demonstrated. |
| Catalog input leaks realized returns | Reviewed chunk whitelist excludes daily_stock/high_signal. |
| XML 24:00 rejection is necessarily wrong | XBRL period rules explicitly forbid that representation; generic XML time acceptance does not settle XBRL. |
| Strict historical cutoff versus event-time menu cutoff is an off-by-one defect | Distinct intended boundaries: reads < as_of, event evidence ≤ event time. |
| Seven graph-test failures reveal code problems | Missing temporary .env file; exact reruns pass on unchanged code. |
| Two Fiscal-test failures reveal changed behavior | Missing external worklist/cache; exact reruns pass with current fixture bytes. |
| EXP-2 scorer duplication makes reported recall wrong | Independent key deduplication and arithmetic reproduce every published rate. Portable script cleanup still needed. |
| S3, recovery, or contradiction detectors are all bot overbuilding | Original approved BUILD requires them; only their explicitly optional parts may stay off. |
| Current evidence binder is the native materializer | Different capabilities; native creation remains dormant. |
| A plan's old hash reference automatically invalidates every later experiment | Check its approved addendum and current pin owner. Historical Plan hash 51966848… is superseded by the approved current bytes; archived originals remain history. |

## 9. Does the task list match the intended scope?

**Mostly as a route to an initial Fiscal system, but it is not a complete, already-ratified specification of the owner's comprehensive endpoint.** Most large missing capabilities are original requirements rather than bot additions. The main risks are conflicting later amendments, old machinery left in donor tools, treating development proof as qualification, and a first-release closure that excludes later scope.

### 9.1 Keep, remove, or settle

| Item | Audit judgment |
|---|---|
| Exact source/namespace/entity/dimension/value checks | Required evidence correctness. Their size alone is not overbuilding; D1 shows why exact behavior still needs independent checks. |
| Separate independent identity review | Owner accepted keeping it for this comprehensive build. Do not optimize it away on this audit's authority. |
| Type/family proof, frozen anchors, recovery, gauntlet, required detectors, S3 | Original required design/gates. Removing them for a Fiscal-only shortcut would underbuild the intended safety behavior. |
| Third/extra review solely because a head spans ≥8 companies | Conflicts with later recorded count-free/universal-review policy; Q1 must settle and propagate exact law. Do not accidentally confuse it with the separately specified third grader for seed-link recovery. |
| optional_links in catalog folding | Retired by current BUILD; donor code still carries it. Required cleanup at its owner/callers, not a new feature. |
| Old catalog-first route and unused experimental handlers | Retired/dormant donors. Prove reachability and remove when their replacement lands; do not wire them into the finished system. |
| New provider abstraction, alternate parser/scorer, model deciding source provenance, model for mechanical bookkeeping | Contrary to the recorded smallest-shared-owner direction; not needed to satisfy this design. |
| SQLite / a new operations store | A bot implementation proposal, not original named-technology law. First prove existing atomic ownership is insufficient; one minimal durable lifecycle may be required, a framework is not. |
| 150 real-anchor Fiscal gate | Legitimate qualification work, currently impossible against zero real Drivers. The bounded pilot precedes it; do not manufacture anchors from Guidance/catalog fixtures. |
| Full branch/mutation/population proof | Do not dismiss as bot excess: current project AGENTS explicitly requires class-wide evidence and independent controls. Apply it to real rule owners; avoid redundant layers/tests that merely mirror implementation. |
| News/other channels, non-USD expansion, cross-company slice comparison, third-party guidance, 8-K taxonomy | Cannot all be declared completed/excluded merely by a first-release task list. Keep U01 visible, finalize actual needs, and implement only the resulting requirements. |
| Optional cheap-model program, CLAIM-ON, anchor enrichment, extra detectors, ontology/Bayes proposals | Their explicit triggers/gates apply. Do not count every speculative or optional idea as mandatory completion work. |

The correct response is to finish the missing shared system, reconcile the actual conflicts, and fix the demonstrated defects. The evidence does not justify throwing away the mechanical foundation or adding a second interpretation engine.

### 9.2 Step-by-step crosswalk and actual remaining work

| Step file | What it should close | Current audit disposition |
|---|---|---|
| [step0](LeftOverSteps/step0.md) | Freeze/reconcile starting contracts and implementation state | The audit gives a verified starting record; it does not itself sign/activate new contracts. |
| [step1](LeftOverSteps/step1.md) | Finish keys/experiments and reconcile budget | Open. Historical EXP-0/1/2 are done; remaining keys/EXP-3–6 and exact new runtime qualification are not. Preserve failed work and current 3,070/2,900 totals. |
| [step2](LeftOverSteps/step2.md) | Signed decision memo, precise owner amendments, frozen choices | Open. Propagate confirmed/reconciled behavior into its actual rule owners; do not make the task list the new law. |
| [step3](LeftOverSteps/step3.md) | One shared real semantic reader with the canonical input/reply/accounting path | Missing. Reuse the current boundaries and source proof; no fake semantic replies for certification. |
| [step4](LeftOverSteps/step4.md) | Complete semantic admission/type/family/link/kernel safeguards | Missing. Existing deterministic writer does not close it. |
| [step5](LeftOverSteps/step5.md) | Complete V2 dry-run integration over the real components | Partial. Current injected-reader/existing-Driver route is the starting point. |
| [step6](LeftOverSteps/step6.md) | Atomic public/internal V2 contract and caller switch | Missing. Freeze internal V2 independently and remove incompatible live caller paths only when the switch is ready. |
| [step7](LeftOverSteps/step7.md) | Catalog finalization, qualification, lifecycle/refresh | Partial donor tools; finalizer/rule cleanup/qualified population missing. |
| [step8](LeftOverSteps/step8.md) | Complete reads, continuity, concept/verdict integration, withdrawals | Mostly missing beyond mechanical helpers. Attribution meaning stays with its eventual channel. |
| [step9](LeftOverSteps/step9.md) | 9A reader/source qualification; 9B real 150-anchor tagged-source proof | Open. Current tests and packets are prerequisites, not its PASS. |
| [step10](LeftOverSteps/step10.md) | Minimal reliable runner, lifecycle, cursor/receipt/retry, budgets/health | Missing; build with writes off after stable interfaces. Exact cadence/threshold/stop rules still need their decision packet. |
| [step11](LeftOverSteps/step11.md) | No-write shadow, separately approved schema/pilot, then 9B and bounded rollout | Missing. Small pilot first; 9B before wider harvest. |
| [step12](LeftOverSteps/step12.md) | 12A Guidance retirement, 12B later channels, 12C dormant native materializer | All unfinished at production level. Empty first-release 12B is not comprehensive closure. Native gates still apply. |
| [step13](LeftOverSteps/step13.md) | Reconcile final inventory and prove closure | Not reached. Its first-release exclusions require a separate comprehensive completion record under the owner's stated endpoint. |
| [step14](LeftOverSteps/step14.md) | Optional cheaper-model qualification after closure | Dormant; not required for current completion and not permission for new calls. |

### 9.3 Practical next order

1. **Resolve only the blocking law conflicts:** Q1 and the exact V2/call/key choices. Retain the owner's confirmed comprehensive endpoint and independent-review choice. Do not repeat those permission questions.
2. **Incorporate arithmetic correction `8255d4dc` into active implementation branches at a controlled checkpoint.** The tests/census/regressions are complete for the reviewed snapshots; recheck changed integration points rather than rebuilding these fixes. Preserve old frozen experiment receipts and re-freeze affected future runs. Repair D3 separately after confirming the intended pin heading; the arithmetic patch does not edit the reference inventory.
3. **Complete independent keys and qualification for the canonical AI tasks**, preserving failed attempts and exact budgets; then sign the actual choices. Do not treat an opened development key or a changed input shape as an untouched qualification set.
4. **Build the one shared reader and admission/type/family system** into the existing evidence/conversion/writer owners, with the required link, anchor, validation, detection, and recovery safeguards.
5. **Complete the V2 bridge and atomically switch both contracts/callers** only when the same whole system passes qualification. Close catalog, complete reads/withdrawals/concept/verdict infrastructure, and public receipt semantics.
6. **Certify Fiscal and finish the minimal operating layer with writes off.** Schedules, eligible populations, exact retries, budgets, health/alerts, restart/reconciliation, and protected catalog refresh need explicit final settings.
7. **Prepare a concrete no-write shadow and bounded rollout packet.** Graph schema/sentinels/pilot writes require the owner's explicit approval. The pilot creates lawful anchors; run 9B read-only, then seek separately bounded wider rollout. Fewer than 150 eligible anchors means 9B stays open, not synthetic substitution.
8. **Migrate consumers and retire Guidance lawfully; finish the comprehensive channels and dormant native-XBRL work under their actual designs/gates.** Do not claim full closure after only the Fiscal milestone.

Steps can share existing components, but their semantic qualification, operational proof, and graph activation are separate achievements. The numerical-fix authorization grants no blanket permission to implement or activate this remaining sequence.

## 10. Named unresolved decisions and residual risks

| ID | Precisely what is unresolved | Smallest next resolution |
|---|---|---|
| Q1 | Later count-free identity/standing/retry policy versus original BUILD and existing ≥8-company tools | Obtain/locate the exact narrow owner ruling, then amend all affected eligibility/retry/review/read rules together. Universal independent identity review itself is already accepted. |
| Q2 | Full endpoint beyond Fiscal: which later channels/extensions, their final charters and acceptance bars | Freeze that required set before declaring comprehensive closure. Do not count every brainstorm as required or silently exclude it. |
| Q3 | Whether replaying an identical existing unlinked fact must add newly verified member edges | Resolve FS-18/FS-21 rerun intent, then test the entire merge/fill class if required. |
| Q4 | Final V2 internal/public packet, four-key reply, one-item runtime, model settings, hidden keys and exact promotion evidence | Freeze at the existing owners in Steps 1–6; current staged code/doc prose is not the completed switch. |
| Q5 | Operational cadence, run bounds, health delivery, retries, final lifecycle storage and error budgets | Decide the smallest runner using existing owners; neither this report nor SQLite mention defines production policy. |

Known residual limits after this audit:

- Semantic correctness cannot be guaranteed at 100% by deterministic tests or repeated same-vendor judges. The plan explicitly uses measured bounds, conservative separation, and reversible recovery.
- No populated Driver graph existed, so production series reads, admission/writer operation, recovery, and rollout are unverified.
- Native materialization and its cross-order/suppression/revocation behavior are not established by EXP-1.
- Cache population coverage is finite and partly unparseable/unsupported; uncached documents remain outside D1's source census.
- Existing graph long-number counts describe stored strings, not an independent proof of all printed values.
- Experiments were recomputed from preserved grades; semantic grades themselves were not freshly independently adjudicated.
- Exact live numeric write round-trip and optional live embedding tests were intentionally not run.
- Numerical correction evidence is bounded by the tested classes, the finite source cache, the Python Decimal/resource limits, and the two frozen branch snapshots; no unconditional all-input/all-integration guarantee is claimed.
- Later Steps “owner rulings” beyond the two confirmed choices were not blanket-ratified by this conversation.

These are explicit open items/limits, not claims of success, new required features, or hidden reasons to stop unrelated authorized work.

## 11. How to maintain this one file

### 11.1 Stable and changing sections

- **Keep sections 3–4 stable.** Change behavior only with the actual governing amendment. Record the narrow authority and update the old/new entry; do not append competing interpretations.
- **Update section 2 in place.** A row becomes B only when the entire named component is built and relevant real scenarios pass. Update its evidence/gap cell. Running status changes only after actual deployment plus graph/operation evidence.
- **Replace the current snapshot in sections 5–8** when its code or results change. Preserve a closed defect in one brief sentence with fix commit/test reference; avoid a growing diary.
- **Update sections 9–10 minimally** as gates/decisions close. Do not move an unresolved mandatory requirement into “optional” merely to improve the percentage.
- **Refresh date, commit/tree, affected hashes, exact test scope, graph counts, and remaining exclusions together.** A changed implementation invalidates only the relevant claims until rechecked; never carry old green totals forward as current proof.
- Keep this as the only new-bot handoff. Do not generate another summary/status file for the same purpose. Original signed experiments and governing plans remain separate preserved source evidence.

Before declaring readiness, follow current AGENTS: derive the inventory from live entry points, failure branches, gated work, changed files and database categories; freeze the reviewed snapshot; map every required row to independent tests or a named open item; run focused and full relevant regressions; report remaining semantic/untested risk. No green-count-only readiness claims.

### 11.2 Reproduction notes

Use the repository venv; this environment has python3 but no plain python command. The recorded test invocation used:

    /home/faisal/EventMarketDB/venv/bin/python -m pytest -q \
      -p no:randomly -p no:cacheprovider --no-header --tb=short \
      -m 'not live and not live_write' \
      driver/core driver/relocation .claude/plans/Drivers/experiments/harness

Catalog: the same flags over .claude/plans/Drivers/workflows/tests. Read-only graph lane: the same Core/relocation/harness paths with -m 'live and not live_write'. Fiscal: the thirteen top-level scripts/driver_seed/test*.py files; some tests there access the graph without a live marker, so marker filtering alone does not make them offline.

Use an isolated checkout of the reviewed commit. Supply only the required existing source/worklist fixture bytes and read-only graph configuration; do not copy all credentials or print secrets. Some source helpers read a root .env file directly, rather than environment variables alone. Do not run live_write or enable production paths without actual authorization.

The correction code tree was frozen before full regressions and committed without changing its bytes; only this handoff was added afterward. For the new tests, add `driver/core/test_exact_movement.py driver/relocation/test_exact_sign.py` to the same pytest invocation. The correction's focused integration receipt also included `driver/core/test_driver_validators.py driver/relocation/test_bind_graph_fact.py` (563 tests total). Mutation tests temporarily replaced the two source files inside the independent clone only, restored them in `finally`, and ran before the final freeze.

Temporary checkouts, private fixture copies, credentials, helper scripts, and generated logs/manifests are removed after their findings are consolidated here. This report is the only maintained audit document; the two committed regression-test files are durable code evidence and must be retained. Existing source fixtures, governing plans, and signed experiment artifacts are preserved.

### 11.3 September 7 provenance pins

These pins identify the reviewed bytes, not new semantic authority. A new bot normally needs only this report until changing the corresponding area.

| File | SHA-256 |
|---|---|
| FINAL_DESIGN.md | 4218d73abe6b98ef2ecd325aef8b5e49985101b122e457b39784dee677f32a0b |
| ChannelContract.md | 1062e0fb1b58b4311bb4a03d0a4a42274288c460d22f74a8f75cc803bb04b0dd |
| 15_CandidateFactPacket.md | aa7239edf069dec611678dc9981cebfa6760dedbc79faada95d4bc5c66b7e98c |
| ChannelContractV2.md | d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b |
| BUILD_AND_OPERATIONS.md | b23e225a711a947091c2c64efd501a863dfb05fbb8e668c3e03eb837606f52d5 |
| STATUS_AND_HISTORY.md | a894d8bb9f30008f7ce959cbda509a010f6104052e6b59ab6a63f9ef4b4720ec |
| FableExperimentPlan.md | 7d55a1c849d8ceeaf2b029264287552e9ea08a054bc6b8fb5d6dd347d6942592 |
| FableExperimentWorkOrder.md | e224cf14a1d60141c840fabfb73c18c8ee8e4361cedaf6d3cf27bcd3fee72410 |
| LeftOverSteps/Steps.md | f9190144c071da3003c40b85d7b0064f2df7f16bc62aa9c44064d9ad16e88919 |
| LeftOverSteps/step1.md — pre-existing worktree edit included in plan review | bc5a0043a743547b7e5117aed4bdede75de08031682d8e3cc37d0b70402579e1 |
| experiments/BUDGET.json | 3caf64ad9aed3ae668a21a10ac0c5151ab7b7bc31a173ad8608656b7119a654b |
| WIP/UniversalLocator_Design_2026-07-18.md | 6763d4315a71bd29af2743bca891af865636bfaf39d4af7cd26716aba480db68 |
| WIP/UniversalLocator_SourceLinked_Prose_Simplification_FinalPlan_2026-07-21.md | 8b925a11b41d0ea584a1fdd16f2c74ebc1e277a35cb58b1218b78f93a168b5fb |

Original baseline production bytes (also observed unchanged in the other bots' working copies during isolation):

| Code | SHA-256 |
|---|---|
| driver/relocation/inline_html.py | 66b25fa2488d1b75eb44c02321d06a077a7d381b94bcebab397e4af7a1c8629c |
| driver/core/driver_validators.py | d7bdb4cfaf2f9aa2cc9cca7e974d8622e354b26ea25ed6235714021daa282f48 |
| workflows/fold_catalogs.py | e4d214a215359cdc8e77adfb86cb8f7f9c0e34712b3aeb0f4d02ac3088aef020 |

Correction commit production/test bytes:

| Code | SHA-256 |
|---|---|
| driver/relocation/inline_html.py | c58c1af9d35950b98c9891a00a195a47d5b078e1b258509e14b07b66ffc7f9ea |
| driver/core/driver_validators.py | 4b90aa83595c48e530914c748c00c6c93036559782d7479138cce6eeb7a5dff5 |
| driver/relocation/test_exact_sign.py | 4ec621b3bcec894f8a9e84e3fb070c783d36a040b8594cdcf528de623f061750 |
| driver/core/test_exact_movement.py | 39f66cea404b794a71ffb985f60b9606e98f3745ae2bfec63f7ab21687218b82 |

Preserved source/result pins:

- K-pairs.v1.3: **023fb1ceddbb8ce912b26bf68e7361a7be42cd18fca86bf396f733e80a054896**.
- K-reader.v3: **cf87a09af1c7b7c6f708c8df56d86bfc600edf8c1eaf6e41a8c6ab783b181736**.
- EXP-1 materialized.jsonl: **64518e7474c102ecdebf5cc9483504ab97822f161b9dafee8211009df60522c6**.
- Original proof-kit manifest: **bf9323bc3bdc75a45a7381ac97cf0d4e1403f8754f5ac419abe1136f589c3070**, historical freeze commit prefix 0dd71956.

Original pre-fix audit receipts consolidated before cleanup (historical):

| Receipt | SHA-256 |
|---|---|
| Initial 267-file source manifest | 215ea2f777d49a21ca8e872a401b24be88de41810c8952ba2ae3fe2b92a29c04 |
| AST-derived Python inventory | e6ae1df3e31e187039e6ffb4bdcf7c5d2b68693c0ae0d12849e57cf44d607d08 |
| Core/relocation/harness XML | 2afd3d0e10ce64ffe1ade1985e16719cf56aaca484e2275eef4dd91f45b6ef32 |
| Catalog XML | b3f6e2641668a67bb598d16d3e53124e5d1c001bba47c5bbd77a9818daa21cd2 |
| Initial read-only graph XML | 3202312bc5b3a96fd31b8d2e1aeb338fa8768ac0c31540ba109c9e28926b471d |
| Seven-case graph rerun XML | 830ac885205d9721c9466a3949e6179254f83b08b2b58cbe8edaa745c88eb1a0 |
| Initial Fiscal XML | b66904a93fce87ae9ce58eeb7bb36e62e1da3c57c316ee80143594eed3d43b82 |
| Two-case Fiscal rerun XML | 9744b340ae190a8a923fa2f241a8a79dc0e10e524d7acf9c5305695d242d7c07 |

At the original audit's final source comparison, **all 267 originally manifested files matched their reviewed hashes**, and original HEAD was unchanged. The later correction is the explicit four-file code/test commit recorded above; it does not erase that baseline receipt.

Correction verification receipt hashes (summarized in sections 6/8 before temporary-file cleanup):

| Receipt | SHA-256 |
|---|---|
| full_offline.txt | 553dcc7edf985445b7b8531846959c66c6f051486038ec0c719b2e4e4f0bc0b1 |
| postcommit_gates.txt | 7c15165963251411cd3f235aaa7168b82a6aa600ebdb34d12f7ac865bd48df76 |
| full_live_readonly.txt | 775ea1ab692362d735879cfe9f700cf18c87465e547e9a822f070f4d581ad2da |
| fiscal_catalog.txt | 247e3903bc6b69c4c2e466f4f4bfa29efd5fe539af4508f5323ae22f5b2d869c |
| recovery_focused.txt | 6eb811cc6e4b900433bbf61799ae41c3551e93e4f17754288b9f1fd0b9d152fb |
| mutations.json | 8f61e9fd66f421cd337277526409e6a3ae21f467edc6760306d2d442d98fc61f |
| graph_census.json | 4d5266205d32bdbf0c8d0ffe112f5fae7901cce92656e8374ae2a3486d7e314e |
| cache_census.json | a1dfa4187f0294727ba03824f1c6e514defb5d16d7df9d56f0059a7cb3aaf2c8 |
| fixture_manifest.json | bb8215dad3ddaa22e00e107a6a96fa1c2348daa52f33200c55962e2e6cf01358 |
| function_coverage.json | e0508d47f7d2b4fa36af6be38c4578beca6145b3bcd8c32fd6a9b79d0a2f249e |
| code_inventory.json | df80ad8521b4dd39e3c51e302b3a03e7ddee16c3f73a55a76e7f9a87fd20f51e |

No original plan or another bot's artifact is deleted. This is the only retained audit/status Markdown document.
