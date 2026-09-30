# What the Driver code does today

**It can find filing evidence, check proposed facts and show what it would save. It is not yet the complete system that reads documents, chooses Driver names and saves facts automatically.**

A **Driver** names something you track, such as revenue. A **DriverUpdate** is one fact about it, backed by a source.

A **tagged figure** has labels inside the filing that software can read; this is called XBRL. A **slice** is a company part, such as a region or product.

Compared with your [current design](/home/faisal/EventMarketDB/.claude/plans/Drivers/DriversFinal/DRIVER_RULES_Categorized.md), most existing work is under **DriverUpdate**. Naming and creation are incomplete; price-move explanations are not implemented in this folder.

```text
Your design:
Source → propose name + fact → check meaning → save → read and compare

Existing code:
Find filing evidence → check supplied facts → prepare a save plan
                                                    ↓
                                             real saving blocked
```

A **rehearsal** here means showing proposed changes without saving them. Even if a rehearsal item says “written,” the run’s “dry_run” label means it was only proposed.

## The three folders

| Folder | Plain meaning |
|---|---|
| [channels/fiscal_ai/](/home/faisal/EventMarketDB/driver/channels/fiscal_ai) | Start with a fiscal.ai figure and collect its filing evidence. |
| [relocation/](/home/faisal/EventMarketDB/driver/relocation) | Find a known measure in a filing and prove which figure was found. |
| [core/](/home/faisal/EventMarketDB/driver/core) | Check proposed facts, combine compatible pieces and plan saving. |

**92 files reviewed:** 29 code files, 56 test files, 2 example filings, 4 empty folder markers and 1 older README. The file explanations below are folded so you can open one part at a time.

## What happens in practice

Imagine the source states: **“Revenue was $1.2 billion in Q2.”**

| Step | What the existing code can do |
|---|---|
| Find the evidence | Find supported tagged-filing figures and their own quotes, dates and units. |
| Decide what it means | Receive a proposed name, type and fields from another program or reader. The complete independent meaning check is not connected here. |
| Check the fact | Check its fields, evidence, period and numbers. The newer number converter can turn $1.2 billion into 1,200 million exactly. |
| Prepare saving | Work out whether to add a fact, fill an empty field, retain a conflicting value or make no change. |
| Save it for real | Deliberately disabled in the database code. Tests exercise saving with a simulated database. |

This is an illustration of the pieces, **not a claim that one connected run already performs every step**.

<details>
<summary><strong>Why there are two input paths</strong></summary>

| Older path — called V1 in the files | Newer path — called V2 |
|---|---|
| Receives facts already containing proposed names and details. | Receives source items and calls a reader supplied by the program starting the run. |
| Uses older unit helpers. | Uses explicit number scales and stronger quote-location checks. |
| Can rehearse creating a new metric Driver from supplied approval decisions. | Currently requires the Driver to exist already. |
| Real database writes are blocked. | Real writes are explicitly refused. |

The command-line entry still uses the older path. The newer path is callable from code, but the complete real AI reader and name-approval process are not supplied by this folder.

**Fiscal AI also has two separate pieces:** its existing search command calls an older helper outside this folder, while the newer evidence packer is prepared for later connection. Do not read the folder layout as proof they all run together.

</details>

## Every working file

<details>
<summary><strong>Following one source through the checks</strong></summary>

| File | What it does |
|---|---|
| [driver_write_cli.py](/home/faisal/EventMarketDB/driver/core/driver_write_cli.py) | Runs one document’s proposed facts through checks and produces a save plan and a record of the attempt. |
| [prepared_fact.py](/home/faisal/EventMarketDB/driver/core/prepared_fact.py) | Defines the older input: facts whose names and details have already been proposed. |
| [prepared_fact_v2.py](/home/faisal/EventMarketDB/driver/core/prepared_fact_v2.py) | Defines the newer input: facts with exact number scales and the location of each quote. |
| [driver_fusion.py](/home/faisal/EventMarketDB/driver/core/driver_fusion.py) | Combines compatible pieces of one fact; keeps conflicting values apart. |
| [driver_validators.py](/home/faisal/EventMarketDB/driver/core/driver_validators.py) | Checks allowed fields, states, dates, numbers and required companion facts. It does not judge all meaning. |
| [driver_writer.py](/home/faisal/EventMarketDB/driver/core/driver_writer.py) | Plans whether to add a fact, fill blanks, keep a conflict or leave an existing fact unchanged. |
| [driver_neo4j_adapter.py](/home/faisal/EventMarketDB/driver/core/driver_neo4j_adapter.py) | Reads filings and related data from Neo4j. It currently refuses all real saves. |
| [outcome_codes.py](/home/faisal/EventMarketDB/driver/core/outcome_codes.py) | Lists refusal, hold and skip reasons; the main runner has additional reasons. |

</details>

<details>
<summary><strong>Working out a fact’s details</strong></summary>

| File | What it does |
|---|---|
| [driver_ids.py](/home/faisal/EventMarketDB/driver/core/driver_ids.py) | Builds record IDs from the source, Driver and fact details; checks name shape but does not invent names. |
| [driver_period_resolver.py](/home/faisal/EventMarketDB/driver/core/driver_period_resolver.py) | Turns supported period descriptions into dates, using filing evidence and shared calendar helpers. |
| [driver_units.py](/home/faisal/EventMarketDB/driver/core/driver_units.py) | Older number-and-unit preparation; still contains the old year-over-year default. |
| [unit_resolver.py](/home/faisal/EventMarketDB/driver/core/unit_resolver.py) | Borrows the earlier Guidance unit helper, which uses supplied hints and wording. |
| [slot_convert.py](/home/faisal/EventMarketDB/driver/core/slot_convert.py) | Newer number conversion: multiplies by the supplied scale exactly, without choosing meaning from a Driver name. |
| [driver_member_fold.py](/home/faisal/EventMarketDB/driver/core/driver_member_fold.py) | Formats slice labels and reuses an existing slice only when the complete value matches exactly. |
| [slice_axis_frozen.py](/home/faisal/EventMarketDB/driver/core/slice_axis_frozen.py) | Holds approved filing-breakdown classifications and special cases. |
| [slice_menu.py](/home/faisal/EventMarketDB/driver/core/slice_menu.py) | Builds the company’s available slices and checks exact filing breakdown matches. |

</details>

<details>
<summary><strong>Proving where a figure came from</strong></summary>

| File | What it does |
|---|---|
| [xbrl_attach.py](/home/faisal/EventMarketDB/driver/core/xbrl_attach.py) | Checks a supplied tagged-filing figure against its own filing, quote, dates, units and database rows. |
| [graph_row_contract.py](/home/faisal/EventMarketDB/driver/core/graph_row_contract.py) | Lists the fields that the database reader and filing-evidence checker exchange. |

</details>

<details>
<summary><strong>Finding a figure in a filing</strong></summary>

| File | What it does |
|---|---|
| [locator.py](/home/faisal/EventMarketDB/driver/relocation/locator.py) | Uses a known metric’s description to find candidate figures in tagged filings; each candidate needs its own evidence. |
| [inline_html.py](/home/faisal/EventMarketDB/driver/relocation/inline_html.py) | Matches an official tagged figure to the visible filing text and checks its company, dates, units and number. |
| [exact_numbers.py](/home/faisal/EventMarketDB/driver/relocation/exact_numbers.py) | Compares filing numbers and dates without rounding away differences. |

</details>

<details>
<summary><strong>Preparing Fiscal AI evidence</strong></summary>

| File | What it does |
|---|---|
| [run_code_tier.py](/home/faisal/EventMarketDB/driver/channels/fiscal_ai/run_code_tier.py) | Uses saved fiscal.ai figures to search filings and related earnings releases, recording each result or failure. |
| [fiscal_ai_rules.py](/home/faisal/EventMarketDB/driver/channels/fiscal_ai/fiscal_ai_rules.py) | Leaves out vendor-calculated changes and percentage-share columns that are not original filing figures. |
| [build_packets.py](/home/faisal/EventMarketDB/driver/channels/fiscal_ai/build_packets.py) | Groups found evidence by source document and separates final skips from items that must wait. |
| [public_contract.py](/home/faisal/EventMarketDB/driver/channels/fiscal_ai/public_contract.py) | Converts evidence into the agreed fields; refuses unexpected fields or incomplete filing-breakdown pairs. |
| [route_a_source.py](/home/faisal/EventMarketDB/driver/channels/fiscal_ai/route_a_source.py) | Loads a filing’s tagged figures and saved HTML for the newer search; can fetch missing HTML. |

</details>

<details>
<summary><strong>Small supporting pieces</strong></summary>

| File | What it does |
|---|---|
| [backfill_seam.py](/home/faisal/EventMarketDB/driver/core/backfill_seam.py) | Accepts one suggested Driver when another program reports confirmation; it does not check meaning itself or run history searches. |
| [fact_match.py](/home/faisal/EventMarketDB/driver/core/fact_match.py) | Compares complete produced answers with expected answers for tests. It is not the Driver meaning checker. |

</details>

<details>
<summary><strong>Shared filing names</strong></summary>

| File | What it does |
|---|---|
| [xml_names.py](/home/faisal/EventMarketDB/driver/xml_names.py) | Checks filing-name spelling against XML rules, including names with non-English characters. |

</details>

## Where this fits in your 19 design sections

These rows show useful existing work, **not a claim that any whole section is finished**.

<details>
<summary><strong>Driver — 5 sections</strong></summary>

| Your section | What exists here |
|---|---|
| 1 · Driver record & relationships | Reading name/type and planning a birth quote. No complete current birth record or relationship service. |
| 2a · Fact type | Allowed-type and suffix checks. Choosing the correct meaning comes from outside these checks. |
| 2b · Name | Name-format checks. No complete naming prompt or naming procedure here. |
| 2c · Which name & family | Suffix and companion-name helpers. No complete independent reuse/family approval process. |
| 3 · Creating a Driver | A metric-only rehearsal, based on decisions supplied by another caller. Real creation is blocked. |

</details>

<details>
<summary><strong>DriverUpdate — 9 sections</strong></summary>

| Your section | What exists here |
|---|---|
| U1a · Record & evidence | Fact fields, record identity, source ownership and exact quote checks. |
| U1b · Period | Date and period checks, including borrowed calendar helpers. A duration with only one exact date is held; filling the other from matching evidence is not built. |
| U1c · Slices & measurement tags | Company-part choices, exact filing breakdown checks and tag fields. Meaning choices still need the reader. |
| U1d · States & amounts | Allowed states, exact arithmetic, units, signs, ranges and comparisons. Older/newer paths differ. |
| U2a · Saving | Combining, conflicts, fill-blank plans and simulated all-or-nothing saving. Real database saving is blocked. |
| U2b · Links to filing data | Same-filing evidence checks and proposed member links. The complete optional line-item linking process is not built here. |
| U2c · Reading & comparing | Small helpers for earlier forecasts and their units. No complete history or comparison view. |
| U3a · Forecasts | Forecast field checks and some comparison helpers. No complete withdrawal-spreading or read-time movement process. |
| U3b · Surprises | Companion-fact checks and some comparison handling. Meaning decisions and preparation-path differences remain. |

</details>

<details>
<summary><strong>System — 5 sections</strong></summary>

| Your section | What exists here |
|---|---|
| S1 · Ground rules | Many structural checks, refusal paths and protected evidence copies. No complete AI approval service. |
| S2 · Purpose, sources & companies | Fiscal AI filing collection and database reads. No complete four-channel system or company-coverage refresh. |
| S3 · Processing, timing & retries | Per-item outcomes, run records and a small history-match helper. No automatic live/history scheduler or full retry service. |
| S4 · AI use & testing | Extensive code tests and recorded-answer rehearsals. These do not measure the current real AI’s full accuracy. |
| S5 · Price-move explanations | No verdict-saving or `EXPLAINED_BY` implementation in this folder. It remains part of your release design. |

</details>

## Before reusing this code

Some behavior follows older rules. Open this only when you reach the relevant design section.

<details>
<summary><strong>Important differences from your current rules</strong></summary>

Only the differences needed to understand reuse are listed here; the [scratchpad](/home/faisal/EventMarketDB/.claude/plans/Drivers/WIP/Driver_Code_Reading_Scratchpad_2026-09-29.md) keeps the supporting details.

| Current design | Existing code |
|---|---|
| Unstated growth basis stays unknown (3.33). | The older unit path still defaults some growth to year-over-year. |
| New Driver has approved meaning and frozen first-quote context (2.1, 2.26, 2.37). | The rehearsal takes supplied metric decisions, lacks full context, and can plan an unknown-state first fact. |
| Surprise handling follows the same rules (4.10–4.12). | A wordless proposed beat exactly at consensus is corrected in the older preparation path, but not the newer conversion. |
| Broad document reading and ongoing updates (8.10, 8.16). | The newer locator requires tagged filing HTML; it does not read untagged prose, transcripts or news. |
| Driver stages and after-save repair are removed (2.2, 6.20). | There is no such running service here. Some comments still use older repair language. Run logs simply record processing attempts. |

The locator currently recognizes **dollars, share counts and dollars per share**. That is its search limit, not the limit of every number checker in Core.

</details>

<details>
<summary><strong>Code this folder borrows</strong></summary>

| Outside location | What it supplies |
|---|---|
| [guidance_ids.py](/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/guidance_ids.py) and [fiscal_math.py](/home/faisal/EventMarketDB/.claude/skills/earnings-orchestrator/scripts/fiscal_math.py) | Existing unit and calendar helpers. The period path can also read dates from old Guidance records and caches; it does not copy those facts into Drivers. |
| [scripts/driver_seed/](/home/faisal/EventMarketDB/scripts/driver_seed) | The older Fiscal AI figure finder, saved examples and additional channel tests. |
| [scripts/earnings/](/home/faisal/EventMarketDB/scripts/earnings) | Matching an earnings release to the relevant quarterly or annual filing. |
| [data/driver_catalog_seed/](/home/faisal/EventMarketDB/data/driver_catalog_seed) | Saved worklists, source evidence and recorded test answers. |

</details>

## Tests and other files

Tests describe what has been checked. A passing test can preserve an older rule, so the latest rules still decide what the design should do.

<details>
<summary><strong>The 35 Core test files — one sentence each</strong></summary>

| File | What it does |
|---|---|
| [test_adjusted_preservation.py](/home/faisal/EventMarketDB/driver/core/test_adjusted_preservation.py) | Keeps an adjusted measurement tag through preparation and evidence reconstruction. |
| [test_admissions_handoff.py](/home/faisal/EventMarketDB/driver/core/test_admissions_handoff.py) | Checks supplied metric-creation decisions and their rehearsal plans; creates no real Drivers. |
| [test_backfill_seam.py](/home/faisal/EventMarketDB/driver/core/test_backfill_seam.py) | Checks one suggestion and an explicit confirmation from its caller; refuses missing confirmation or multiple suggestions. |
| [test_dimension_expanded_identity.py](/home/faisal/EventMarketDB/driver/core/test_dimension_expanded_identity.py) | Distinguishes filing names by their full naming authority, not just their short prefix. |
| [test_dimension_identity_at_the_door.py](/home/faisal/EventMarketDB/driver/core/test_dimension_identity_at_the_door.py) | Checks complete filing-breakdown identity at the fact-input boundary. |
| [test_driver_fusion.py](/home/faisal/EventMarketDB/driver/core/test_driver_fusion.py) | Checks combination order, conflicting values and conflicting filing breakdowns. |
| [test_driver_ids.py](/home/faisal/EventMarketDB/driver/core/test_driver_ids.py) | Checks consistent record identifiers and malformed input rejection. |
| [test_driver_member_fold.py](/home/faisal/EventMarketDB/driver/core/test_driver_member_fold.py) | Checks exact slice reuse and preservation of filing-member links. |
| [test_driver_period_resolver.py](/home/faisal/EventMarketDB/driver/core/test_driver_period_resolver.py) | Checks dates, missing periods, ambiguity and the borrowed calendar helpers. |
| [test_driver_units.py](/home/faisal/EventMarketDB/driver/core/test_driver_units.py) | Checks the older unit path, including its older growth-basis behavior. |
| [test_driver_validators.py](/home/faisal/EventMarketDB/driver/core/test_driver_validators.py) | Checks the shared rules for fact fields, states, values and companion facts. |
| [test_driver_write_cli.py](/home/faisal/EventMarketDB/driver/core/test_driver_write_cli.py) | Exercises the older route using an in-memory database substitute, including failed saves. |
| [test_driver_writer.py](/home/faisal/EventMarketDB/driver/core/test_driver_writer.py) | Checks add, unchanged, fill-blank and conflict plans. |
| [test_exact_movement.py](/home/faisal/EventMarketDB/driver/core/test_exact_movement.py) | Checks forecast comparisons with independent exact arithmetic. |
| [test_graph_qname_shape.py](/home/faisal/EventMarketDB/driver/core/test_graph_qname_shape.py) | Refuses malformed official filing names. |
| [test_neo4j_adapter_readonly.py](/home/faisal/EventMarketDB/driver/core/test_neo4j_adapter_readonly.py) | Checks real database reads and local bad-data cases; verifies that writing is refused. |
| [test_neo4j_numeric_roundtrip.py](/home/faisal/EventMarketDB/driver/core/test_neo4j_numeric_roundtrip.py) | Creates and deletes a database probe to check number storage. Not run in this review. |
| [test_prepared_fact.py](/home/faisal/EventMarketDB/driver/core/test_prepared_fact.py) | Checks the older fact input and its number and filing-evidence fields. |
| [test_prepared_fact_v2.py](/home/faisal/EventMarketDB/driver/core/test_prepared_fact_v2.py) | Checks the newer input, exact scales, quote locations and field ownership. |
| [test_raw_fact_accounting.py](/home/faisal/EventMarketDB/driver/core/test_raw_fact_accounting.py) | Ensures no submitted item disappears when facts split, combine, fail or produce nothing. |
| [test_round10_event_boundary.py](/home/faisal/EventMarketDB/driver/core/test_round10_event_boundary.py) | Checks malformed events, repeated rows, protected evidence and failed reads. |
| [test_round11_outcomes.py](/home/faisal/EventMarketDB/driver/core/test_round11_outcomes.py) | Checks that failures receive the right recorded reason. |
| [test_round12_exact_scale.py](/home/faisal/EventMarketDB/driver/core/test_round12_exact_scale.py) | Checks exact scale multiplication and refusal of numbers too large to store safely. |
| [test_round12_pure_unit_law.py](/home/faisal/EventMarketDB/driver/core/test_round12_pure_unit_law.py) | Checks filing-unit compatibility without using the older meaning-guessing helper. |
| [test_round13_quote_occurrence.py](/home/faisal/EventMarketDB/driver/core/test_round13_quote_occurrence.py) | Refuses invented quotes and quotes pointing to the wrong occurrence. |
| [test_round14_evidence_matrix.py](/home/faisal/EventMarketDB/driver/core/test_round14_evidence_matrix.py) | Changes quote locations and table context to test that evidence cannot silently move. |
| [test_round15_audit_evidence.py](/home/faisal/EventMarketDB/driver/core/test_round15_audit_evidence.py) | Checks that excluded database rows and item outcomes remain visible in the run record. |
| [test_round8_xbrl_binding.py](/home/faisal/EventMarketDB/driver/core/test_round8_xbrl_binding.py) | Checks filing ownership, dates, units, changed source content and temporary failures. |
| [test_round9_corrections.py](/home/faisal/EventMarketDB/driver/core/test_round9_corrections.py) | Checks signs, complete breakdowns and evidence from one document. |
| [test_s4_rehearsal.py](/home/faisal/EventMarketDB/driver/core/test_s4_rehearsal.py) | Replays recorded AI answers with real database reads; checks connections, not AI accuracy. |
| [test_slice_menu.py](/home/faisal/EventMarketDB/driver/core/test_slice_menu.py) | Checks available slice choices and exact filing breakdown matches. |
| [test_unit_identity_expanded.py](/home/faisal/EventMarketDB/driver/core/test_unit_identity_expanded.py) | Checks official unit identity rather than trusting short labels. |
| [test_unit_resolver.py](/home/faisal/EventMarketDB/driver/core/test_unit_resolver.py) | Checks the borrowed older unit helper and where it was loaded from. |
| [test_v2_attacks.py](/home/faisal/EventMarketDB/driver/core/test_v2_attacks.py) | Tries false evidence, source swapping, changed inputs and number-precision errors. |
| [test_v2_event_route.py](/home/faisal/EventMarketDB/driver/core/test_v2_event_route.py) | Checks the newer route with a supplied test reader, including refusal of real writes. |

</details>

<details>
<summary><strong>The 21 filing-search test files — one sentence each</strong></summary>

| File | What it does |
|---|---|
| [test_anchor_schema_probe.py](/home/faisal/EventMarketDB/driver/relocation/test_anchor_schema_probe.py) | Checks rebuilding a complete search description from a saved metric fact. |
| [test_bind_graph_fact.py](/home/faisal/EventMarketDB/driver/relocation/test_bind_graph_fact.py) | Refuses wrong or ambiguous matches between database figures and filing evidence. |
| [test_context_content_model.py](/home/faisal/EventMarketDB/driver/relocation/test_context_content_model.py) | Separates invalid filing context from valid context this reader cannot handle. |
| [test_evidence_writer_contract.py](/home/faisal/EventMarketDB/driver/relocation/test_evidence_writer_contract.py) | Checks the four fields returned as source evidence. |
| [test_exact_numbers.py](/home/faisal/EventMarketDB/driver/relocation/test_exact_numbers.py) | Checks exact arithmetic and date comparison. |
| [test_exact_sign.py](/home/faisal/EventMarketDB/driver/relocation/test_exact_sign.py) | Checks that making a long number negative never rounds it. |
| [test_locator_routes.py](/home/faisal/EventMarketDB/driver/relocation/test_locator_routes.py) | Keeps older unsupported text and malformed requests from producing facts. |
| [test_match_facts.py](/home/faisal/EventMarketDB/driver/relocation/test_match_facts.py) | Confirms the retired name-string matcher refuses requests. |
| [test_multipart_anchor_ce.py](/home/faisal/EventMarketDB/driver/relocation/test_multipart_anchor_ce.py) | Finds a real older Celanese figure with both business and geography breakdowns. |
| [test_neutral_boundary.py](/home/faisal/EventMarketDB/driver/relocation/test_neutral_boundary.py) | Checks that shared search does not depend on the fiscal.ai channel. |
| [test_packet_items_through_the_door.py](/home/faisal/EventMarketDB/driver/relocation/test_packet_items_through_the_door.py) | Passes all eleven saved sample items through Core’s filing-evidence checks. |
| [test_parser_encoding_ownership.py](/home/faisal/EventMarketDB/driver/relocation/test_parser_encoding_ownership.py) | Checks that reading a filing preserves characters and official identities. |
| [test_phase3_prose_removal.py](/home/faisal/EventMarketDB/driver/relocation/test_phase3_prose_removal.py) | Checks that the removed plain-text search remains removed. |
| [test_real_726_end_to_end.py](/home/faisal/EventMarketDB/driver/relocation/test_real_726_end_to_end.py) | Checks a real Celanese $726 million figure against its filing, database row and Core input. |
| [test_route_a.py](/home/faisal/EventMarketDB/driver/relocation/test_route_a.py) | Checks tagged-figure search, local quotes, printed values and ambiguous matches. |
| [test_route_a_unit_identity.py](/home/faisal/EventMarketDB/driver/relocation/test_route_a_unit_identity.py) | Checks a unit’s official meaning and agreement with the database. |
| [test_row_label_span.py](/home/faisal/EventMarketDB/driver/relocation/test_row_label_span.py) | Checks that labels, headers and quotes come from the correct visible locations. |
| [test_semantic_fact_value.py](/home/faisal/EventMarketDB/driver/relocation/test_semantic_fact_value.py) | Checks the official tagged number separately from its visible quote. |
| [test_transform_registry.py](/home/faisal/EventMarketDB/driver/relocation/test_transform_registry.py) | Checks standard ways of reading printed numbers and refuses unsupported ones. |
| [test_two_view_bridge.py](/home/faisal/EventMarketDB/driver/relocation/test_two_view_bridge.py) | Keeps official filing data correctly paired with visible page text. |
| [test_unit_handoff_census.py](/home/faisal/EventMarketDB/driver/relocation/test_unit_handoff_census.py) | Checks every offered unit row from one real filing through search and evidence preparation. |

</details>

<details>
<summary><strong>The README, two example filings and four empty files</strong></summary>

| File | What it does |
|---|---|
| [README.md](/home/faisal/EventMarketDB/driver/README.md) | An older folder plan. Some listed future parts are not built; current rules take precedence. |
| [0001306830-24-000098.htm](/home/faisal/EventMarketDB/driver/relocation/fixtures/0001306830-24-000098.htm) | A real Celanese Q1 2024 filing used to check finding older evidence. |
| [0001306830-25-000105.htm](/home/faisal/EventMarketDB/driver/relocation/fixtures/0001306830-25-000105.htm) | A real Celanese Q1 2025 filing containing the prior-year comparison. |
| [__init__.py](/home/faisal/EventMarketDB/driver/__init__.py) | Empty; lets Python treat this folder as a group of code files. |
| [__init__.py](/home/faisal/EventMarketDB/driver/channels/__init__.py) | Empty; marks the channel code folder. |
| [__init__.py](/home/faisal/EventMarketDB/driver/channels/fiscal_ai/__init__.py) | Empty; marks the Fiscal AI code folder. |
| [__init__.py](/home/faisal/EventMarketDB/driver/core/__init__.py) | Empty; marks the Core code folder. |

Generated cache files contain no design and are excluded.

</details>

## What I verified

**3,165 local checks and 31 selected real-data checks passed.** This does not prove the AI accuracy target or readiness to run automatically.

<details>
<summary><strong>What those checks prove, and their limits</strong></summary>

- Read the working files, followed their callers and compared them with the current categorized rules.
- **3,165 local checks passed.** The 58 database-related selections were excluded from that run.
- **31 selected real-data checks passed**, using database reads only, including a recorded-answer rehearsal and the real $726 million filing example.
- Direct database reads found **0 Drivers, 0 DriverUpdates and 0 DriverPeriods**. The required Driver database setup is not present.
- Tried two small controlled examples showing the unknown-state birth gap and the surprise-preparation difference.

No AI calls or database writes were made. These results prove specific code behavior, **not the less-than-1% AI error target or production readiness**.

</details>

**Suggested first read:** the summary, then the Driver table. It shows exactly where your naming redesign will need decisions, while the existing fact-checking work can remain in the background.
