# Driver code reading scratchpad

## What this review is for

Explain every file under `driver/` in plain words, using the current `DRIVER_RULES_Categorized.md` as the design to compare against. This is an explanation of existing code, not a new design or permission to activate it.

The short guide will live at `DriversFinal/DRIVER_CODE_GUIDE.md`. This scratchpad holds the supporting notes so the guide can stay short.

## Review passes

1. List every file and follow the actual starting points.
2. Read the working code, its checks and its outside dependencies; map each part to the current design.
3. Try representative cases without calling AI or changing the database; distinguish working pieces from a complete working system.
4. Review the explanation for missing files, incorrect claims and unnecessary words.

## First findings

- There are 92 non-generated files: 29 code files, 56 test files, two example filings, four empty package markers and one README.
- The README is dated July 15 and describes a target layout. It is not proof that those parts have been built, or that its older decisions still apply.
- The new rules file and the owner's later decisions take precedence over older comments and plans.
- The current task authorizes this scratchpad and an explanatory guide only. Code, rules and Notion stay unchanged.

## Questions to check from the code

- What can start a run, and what does that run receive and produce?
- Which Fiscal AI paths actually locate a number in a source document?
- Which meaning decisions arrive from another component rather than being made in this folder?
- Which checks work with real database reads, and which work only in rehearsal?
- Where does the code still follow the earlier lifecycle, naming or fact rules?
- Which of the current design's 19 homes have useful code, partial code or no implementation here?
- What do all 56 test files actually check, and what do they not prove?

## Snapshot

The file list and content fingerprints below record what was reviewed. Generated Python caches are excluded.


Commit: `30b6cc0260fb99cd3da0c50941942b2a893a3cc9`.

Rules file fingerprint: `8813d0f8dd3edd5d911ff9a9d10d25f529151ce55357ef3705441a675e52eb86`.

<details>
<summary>Every reviewed file and its fingerprint</summary>

| File | Lines | SHA256 |
|---|---:|---|
| `driver/README.md` | 76 | `2ff284206b620f3769c79e6acadf4f8c874d44593d0c2240d75ffdc8f547b461` |
| `driver/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `driver/channels/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `driver/channels/fiscal_ai/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `driver/channels/fiscal_ai/build_packets.py` | 186 | `fce8c5123a30fb2577149cdf7074e2a84df62f228d25ee61971b921f6bb0165e` |
| `driver/channels/fiscal_ai/fiscal_ai_rules.py` | 23 | `958068feec5630c0104d30e93db9a3c4f09856b46b462b2cb852814769c4bc25` |
| `driver/channels/fiscal_ai/public_contract.py` | 62 | `7e853176ff4856ff07bf9e7e1a8537d6e1084ee1cc3dd5bbd2a767c0856c5b51` |
| `driver/channels/fiscal_ai/route_a_source.py` | 138 | `006163b90ccfbe22795ef93202468754cf0ed466bb079902bf6438fff0602f31` |
| `driver/channels/fiscal_ai/run_code_tier.py` | 388 | `5371742664482aaf83592bef18899bfe059ff204724ad9a175453e7d548abb5d` |
| `driver/core/__init__.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `driver/core/backfill_seam.py` | 38 | `aa1b7861fda31acddbd2552c89583d621ad638121cc33a41cdd87da6b9fdd732` |
| `driver/core/driver_fusion.py` | 134 | `f692340b9930c167789fc8ed5f1bec3be62ec3b8d7ff20c93b3a12b76074b9ab` |
| `driver/core/driver_ids.py` | 407 | `7823875e62658ff10314ab278e52bd83d35a7a0f21d9acf2971a39e283412f64` |
| `driver/core/driver_member_fold.py` | 31 | `3a8753a47f1a0288956a65c6d978492bcacc3e0346c15e0e25d071e7df14b83c` |
| `driver/core/driver_neo4j_adapter.py` | 677 | `52ebd0aee4c29d935d6a35221bef86311640bada22ab896681579f567700b9c9` |
| `driver/core/driver_period_resolver.py` | 552 | `58431a987f67c10c968ebf2cabbd1eb3aa13cb2c6d9d5fb57de6838c37be4eab` |
| `driver/core/driver_units.py` | 170 | `7e158626006860c4baa80e301be145787d3546a77c6f2f5ad2831c1b886fab06` |
| `driver/core/driver_validators.py` | 643 | `4b90aa83595c48e530914c748c00c6c93036559782d7479138cce6eeb7a5dff5` |
| `driver/core/driver_write_cli.py` | 1573 | `2f716b3640cfd13b0a85278231331e7450973b748cc424c6e49f4684618646cf` |
| `driver/core/driver_writer.py` | 414 | `52dd6c3083434caa6afeed87f21c24a731a8de6c5146925c2fca3351a1cdfc71` |
| `driver/core/fact_match.py` | 141 | `bf6f0c922ef1f443fa16b01c4d80d87b445895d48b7da5fa772964de21304497` |
| `driver/core/graph_row_contract.py` | 58 | `1d14a6cb068597cb930cfd643be14a0b00ed07a79edba771a0f4de8da67329f1` |
| `driver/core/outcome_codes.py` | 64 | `9bc75bda8402d7d0bd4a1f774c29e7420260edb69a79a338600d545552c4a897` |
| `driver/core/prepared_fact.py` | 241 | `aaef4959c7bdda4aee3cdab1e3bdeb436ef4a34cfea211caaba2db3ee42b56c5` |
| `driver/core/prepared_fact_v2.py` | 698 | `a98d6c64c6c429d8577c80d8dc0a30cb62919428d8a9a1cd664167fd5d3352fd` |
| `driver/core/slice_axis_frozen.py` | 131 | `917d61c8416191797741678b59f49843048a39a73f9741fcab0b23cdb08f7b76` |
| `driver/core/slice_menu.py` | 308 | `81885b0f3c8326d37514dcce9a137209b8ef1ed2e4889a0260e04403a6522321` |
| `driver/core/slot_convert.py` | 299 | `1e831b09b255b5653b23b729de6952e187e6923caff2c1e83330ef5ddfcddbc2` |
| `driver/core/test_adjusted_preservation.py` | 148 | `fd03bc05256d28908f82aee618c61affdee7b03758177758b4bcac43f37f0755` |
| `driver/core/test_admissions_handoff.py` | 286 | `faa21a08af1b0294e51a4c7b3cec4bab5010856e6c0a0981823ee9a9ab74fafd` |
| `driver/core/test_backfill_seam.py` | 81 | `ed44edc9be2acf724c0cf40f9cf81a6158aa356eb27a8d3d31bd40d0bc774562` |
| `driver/core/test_dimension_expanded_identity.py` | 194 | `b4db1c10fd5dbb7b531a0f6f2b013ba658e4001b24f5e8c696cc54022084fc2c` |
| `driver/core/test_dimension_identity_at_the_door.py` | 193 | `aca66121054a1fae6b57732f4ff808bcda8e3cd82ea3ea307c90be05f423bed7` |
| `driver/core/test_driver_fusion.py` | 199 | `d508890e46dd779796eecd40b7d0c18a0ded587f43c9cda14ed8f903371a6d22` |
| `driver/core/test_driver_ids.py` | 667 | `c11ce371f7572ea9414ff7a4f2565705fcab8474a4869780341111fb0d93dd3b` |
| `driver/core/test_driver_member_fold.py` | 261 | `3c379d6cb425f049164cd2918ed1a9904d93965fabf6a200fbcd664a9c04494b` |
| `driver/core/test_driver_period_resolver.py` | 1225 | `e76babe43b0296c99d92cf4cd02ea9b1d9f539e04a4ca225e9154872b992b660` |
| `driver/core/test_driver_units.py` | 284 | `a23ae4bb9bb7a36ec0795ee537236711417077dfb7055a1ce310c9c676fddc87` |
| `driver/core/test_driver_validators.py` | 906 | `dd6cf8568030664bb0b30ccb2ae139d6241e98c84fe2d087f57fe7deba9bdd12` |
| `driver/core/test_driver_write_cli.py` | 1020 | `6ee538eb7735c1afabefab361c3b2234e47b1ae537f50088f24fbf2fb1bbda35` |
| `driver/core/test_driver_writer.py` | 354 | `2cc2f18b80123d4319bd54ef223c166d40970af65bc09d80237066a52e45d872` |
| `driver/core/test_exact_movement.py` | 193 | `39f66cea404b794a71ffb985f60b9606e98f3745ae2bfec63f7ab21687218b82` |
| `driver/core/test_graph_qname_shape.py` | 117 | `dc269e847495f99a1dad9ecd59b4e054def417b70f7e1757366705c8cee04ce4` |
| `driver/core/test_neo4j_adapter_readonly.py` | 605 | `2c749688326684c29dc189cb965886df65f859a414c89c8907bc4c52dbe9632c` |
| `driver/core/test_neo4j_numeric_roundtrip.py` | 119 | `6d56c8abe6d06ece5cb0cbfae35bd5542e5b5c37060a00c3f1d9ed51294b0410` |
| `driver/core/test_prepared_fact.py` | 284 | `1ec51acac828759877bbb8166ebfafe9c3add8df1279d12a9530d43bac49b4c0` |
| `driver/core/test_prepared_fact_v2.py` | 1142 | `58b57146fa0bf907f376bd577b776178ad474a405570d5a2d0870a64be07450f` |
| `driver/core/test_raw_fact_accounting.py` | 640 | `3bf0001aea47bf9b16d1059324900d6203c27f235ce84b53707bfab7ad8ff2a0` |
| `driver/core/test_round10_event_boundary.py` | 1670 | `43cb0cd92c2eb8bb73a74bcc279ba68f15989983498936ca8e87f4bbe2898b47` |
| `driver/core/test_round11_outcomes.py` | 769 | `6db042107f263b43fe913acc232c87c8bb31d362fbf01bcd67b755b4db763c7e` |
| `driver/core/test_round12_exact_scale.py` | 366 | `2acd14031f8062281ffa375e8117de35a629455e9a4bfc878de5b57bca0ce586` |
| `driver/core/test_round12_pure_unit_law.py` | 771 | `b8d6fd39112d8b0db085618516ea4da9799b3748c6314f6722decc51e7a1dfdb` |
| `driver/core/test_round13_quote_occurrence.py` | 247 | `0545dc17799848d9f48c8cfb084addc37cb1544d37958a652132c26a56a735c2` |
| `driver/core/test_round14_evidence_matrix.py` | 817 | `f0701fdb8303235c126a4eba9ce5ac976a96225b6e3faf27ed13e4f4a54c057b` |
| `driver/core/test_round15_audit_evidence.py` | 1100 | `ddd4884de4846df73ed2d93bad5b684487de43671ef4afb38bea44b9bf7c5766` |
| `driver/core/test_round8_xbrl_binding.py` | 1492 | `cab72b083a7b9c6090e0e48d3ea5324d586709c97091184668938ace624b0b11` |
| `driver/core/test_round9_corrections.py` | 235 | `66eff0a71e898077d3a899fe3b42cf12817db37b930e4bd8ef7e713d7738e19b` |
| `driver/core/test_s4_rehearsal.py` | 417 | `91a4a966ded00ae83c478a5d3b4c3930bb031960a5e14fe41b555cee6ef8e90f` |
| `driver/core/test_slice_menu.py` | 253 | `158a34885fd4b0682d70b0afb566defe4584119458ea1fe44ffd4b8c46ddb6dc` |
| `driver/core/test_unit_identity_expanded.py` | 195 | `0ad94ec5fce908eebd1e980e292e0c7fa0b5e7effca245273bd069e96e5c9787` |
| `driver/core/test_unit_resolver.py` | 231 | `ab80f513c2c63a58d1d735c09b3684b3a4734612f6f7af227bf09c171e0ec8c5` |
| `driver/core/test_v2_attacks.py` | 1639 | `f8a8baa85be0f0d61a22c51dd3eb64e72fcae89ab13064faf04eb87b9e7c5548` |
| `driver/core/test_v2_event_route.py` | 2593 | `b9d90c1d8e84aa0c574b3ddbf8b4fa7be1c204c5fcc000eefad0ca4f3208a2c5` |
| `driver/core/unit_resolver.py` | 267 | `1d4b6c44b14e5fae8600ca0b7a0643e53816342b86a2ea3e7b2cc3bb96b41d5a` |
| `driver/core/xbrl_attach.py` | 1316 | `a3ec7ad6f656b628d1d446cb0c8d9641fd0bef9f2f0376258af3d78da8504290` |
| `driver/relocation/exact_numbers.py` | 812 | `0ab9d86e34e94bc0b11470b0aa59f8b070e2d09e1134ff18ad37cf1839f2383a` |
| `driver/relocation/fixtures/0001306830-24-000098.htm` | 8 | `2c0a5134a44e6b930c16e8b2a4013d10fb02373c7005652aa328e6b2df681825` |
| `driver/relocation/fixtures/0001306830-25-000105.htm` | 8 | `a0114fbad66d39012cf257cad30374e6d45fc868e90a6663f6ceb69294a0c919` |
| `driver/relocation/inline_html.py` | 4412 | `c58c1af9d35950b98c9891a00a195a47d5b078e1b258509e14b07b66ffc7f9ea` |
| `driver/relocation/locator.py` | 1344 | `ead92bdb549b49f0bfe7d60430735cc1f432c7a6145bb7057c26bb10c69b8b82` |
| `driver/relocation/test_anchor_schema_probe.py` | 523 | `240521fc3ec834b6b6a66551062d7c5ee9e4a5ddbd75eac135985e3f15087432` |
| `driver/relocation/test_bind_graph_fact.py` | 2048 | `6839743d099c45bb53bfc397ce59ecb973f7220f133696317d90f8082bb7b547` |
| `driver/relocation/test_context_content_model.py` | 908 | `4b2dae770c7b9e4edafeb631b48dad7ef9fa11794c5fa7c123d7e2ea1e637add` |
| `driver/relocation/test_evidence_writer_contract.py` | 28 | `5e80ded054d502b5305a378d1cf4ccea7cedd26865e8716f1f4e95b830a254ed` |
| `driver/relocation/test_exact_numbers.py` | 189 | `41f11318386a1e5318693675e6ebb6be51c1ebf9422815f65c13763d294ad3e2` |
| `driver/relocation/test_exact_sign.py` | 107 | `4ec621b3bcec894f8a9e84e3fb070c783d36a040b8594cdcf528de623f061750` |
| `driver/relocation/test_locator_routes.py` | 163 | `35a9950b5f721c9f176a3e40b1c1708c20bba0ef14c7865962f825554ce4c937` |
| `driver/relocation/test_match_facts.py` | 226 | `8d9db28b0eb5479c82e0f7b824aae6c7e3cfc52d44074ea1e2c2fef3a322bf54` |
| `driver/relocation/test_multipart_anchor_ce.py` | 165 | `d612b5b583f455966a812cb74f6fffa2d4ccb484369f174b332ced8141a958ab` |
| `driver/relocation/test_neutral_boundary.py` | 54 | `4ef44bddc6d153e489593a29c4da04b8e5aa11fdc87e3e2c14d2a6d91e9da8c1` |
| `driver/relocation/test_packet_items_through_the_door.py` | 188 | `bd9bffe0de1c8d26fc2387fb9e7c34230d5ad11ebd488fb0f3fb238a26e142f3` |
| `driver/relocation/test_parser_encoding_ownership.py` | 284 | `7bbecdb3f28d5f4ded1dceb3214d693195c3be3ad76044c0e40a7e1ec6798932` |
| `driver/relocation/test_phase3_prose_removal.py` | 31 | `2019aec63fd87be77727f497794cb6e5a6e7926b85d09a0d42baa078f7771c21` |
| `driver/relocation/test_real_726_end_to_end.py` | 540 | `02b556d0b411b066baa8c7ac3ec9ae54111cbf337abd8af61f8a19e7ccae805e` |
| `driver/relocation/test_route_a.py` | 1060 | `ab62383c70b94f61932ee8c829421d365a0c1a7811a3d6361707e2cc9249c07b` |
| `driver/relocation/test_route_a_unit_identity.py` | 232 | `eda8d730a67929473b0b6b8d5fdecbdd317954f9ff407e6b0deedfdf1cab19bf` |
| `driver/relocation/test_row_label_span.py` | 1352 | `12147e51862b2c488f900b5cdcb12951cb534a4af28613292780d97fd8486084` |
| `driver/relocation/test_semantic_fact_value.py` | 644 | `b3a2e9e1dfb8a42d6f04e0c9e99696f811d20729b257a0694785b669c7f20831` |
| `driver/relocation/test_transform_registry.py` | 452 | `e73e9d7b6f234f60befa0cd38739befd01f0b6bf63f380be1d49b299cbecb673` |
| `driver/relocation/test_two_view_bridge.py` | 1164 | `7170a51e8ee9d198ac68f65ff11e70b5d1a5549598db5dad2c1a18a11cda3f1d` |
| `driver/relocation/test_unit_handoff_census.py` | 253 | `851359901bda2b45d2ff826e60103499b7b2657af23df0f00653d414736b3ce5` |
| `driver/xml_names.py` | 58 | `f6cad0ca0e1fcda57d35d09a661f6c976e30b6d103944d468c5dbae7876db564` |

</details>

## Pass 2 — What the code actually connects

- The folder contains useful pieces, but not the complete process that reads a new document, invents and checks a name, and saves the fact.
- There are two ways into `run_event`: an older path receiving already-prepared facts, and a newer path calling a reader supplied by its caller. Neither proves that the real AI reader and independent meaning checker are connected here.
- The older path can rehearse creating a new metric Driver from supplied decisions. Creating those Drivers in the real database is blocked. The newer path currently uses existing Drivers and refuses real writes.
- The real database adapter supports reads but refuses transactions that would write. In-memory tests can still exercise the writer. Those tests are not proof that a production save works.
- Fiscal AI's older harvesting command calls `scripts/driver_seed/locate.py`. It does not call the new `driver/relocation/locator.py` directly. The new packet builder is a separate preparation step.
- Relocation means finding a known figure again in its original filing and proving which number it is. It is not a process for freely reading every kind of document or naming Drivers.
- The current relocation entry point uses filing HTML with embedded official tags. Its old prose fallback has been removed. Its exact unit matcher supports dollars, share counts and dollars per share; it is not universal.
- `xbrl_attach.py` checks that supplied evidence belongs to the filing and its official data. It is not the complete optional link-to-line-item process described in U2b.
- Run logs record what a processing attempt did. They are not the after-save review or repair system that the current design removed.

## Pass 3 — Checks run so far

- The complete local suite, excluding tests marked `live` or `live_write`: **3,165 passed, 58 deselected** in 55.40 seconds. No AI calls, no database writes. Python bytecode and pytest cache writing were disabled.
- The database write probe was deliberately excluded: it creates and deletes a temporary node and needs explicit permission.
- Selected real database read checks are being run separately. Their results will be recorded below; local tests alone are not evidence of current graph contents.
- A separate reviewer ran an in-memory creation example: a new metric with state `unknown` still receives a create-Driver plan. The same valid example with `reported` also passes. This demonstrates that the rehearsal does not yet enforce current rule 2.37's new-Driver evidence gate.
- A separate reviewer compared the two preparation paths: a wordless proposed beat at exactly the consensus value becomes `in_line` in the older path but remains `beat` in the newer conversion. Worded beats and already-`in_line` examples agree. This is a preparation difference, not evidence of bad facts persisted by the newer path, which cannot write.

## How the explanation will stay short

- Put the outcome and a tiny flow first.
- Give each working file one plain sentence, grouped by its job.
- Keep test-file detail folded. The main view should not start with 56 tests.
- Map all 19 current design homes, but label incomplete work plainly.
- Keep technical proof here, with only the material limitations in the guide.

## Pass 3 — Final results and supporting locations

### Executed checks

| Check | Result | What it shows |
|---|---|---|
| All `driver/` tests except `live` and `live_write` | 3,165 passed; 58 deselected; 55.40 seconds | Existing local checks pass, including tests that preserve older rules. |
| Selected live read tests: database adapter, recorded-answer rehearsal, real $726 million example | 31 passed; 65 deselected; 53.77 seconds | Those actual database reads and evidence paths work. This does not exercise real saving or real AI. |
| Direct read-only counts | Driver: 0; DriverUpdate: 0; DriverPeriod: 0 | The current database contains no nodes of these three types. |
| Database setup check | Not ready: all three required uniqueness constraints absent; four dateless period records absent | This is not a fully set-up Driver database. Nothing was created. |

The exact test commands were:

```bash
env -u ENABLE_DRIVER_WRITES -u RUN_NEO4J_ROUNDTRIP_PROBE -u S4_REHEARSAL_OUT \
  PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest driver \
  -m 'not live and not live_write' -p no:cacheprovider -q --tb=short

env -u ENABLE_DRIVER_WRITES -u RUN_NEO4J_ROUNDTRIP_PROBE -u S4_REHEARSAL_OUT \
  PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  driver/core/test_neo4j_adapter_readonly.py \
  driver/core/test_s4_rehearsal.py \
  driver/relocation/test_real_726_end_to_end.py \
  -m live -p no:cacheprovider -q --tb=short
```

The live rehearsal uses recorded proposed names and approval decisions. Its own description says it proves the pieces connect, not how well a real AI reads. The numeric database-write probe was not run. No model calls, database writes or production activation were performed.

### Important findings, with where to look

| Finding | Code or rule location |
|---|---|
| Older creation decisions come from the caller and allow metrics only; creation plus real writing is refused. | `driver/core/driver_write_cli.py:137–182,365–372` |
| New-Driver plan contains first-fact ID and quote, but not frozen context. | `driver/core/driver_write_cli.py:588–611`; current rules 2.1, 2.26, 2.35–2.37 |
| The newer route calls an injected reader, requires an existing Driver and refuses writes. | `driver/core/driver_write_cli.py:1216–1234,1336,1433` |
| Real database saves are refused. | `driver/core/driver_neo4j_adapter.py:593–595` |
| Rehearsal item labels can say written/merged even when nothing was saved. | `driver/core/driver_write_cli.py:897–909`; `test_driver_write_cli.py:134` |
| All-or-nothing saving and last-moment rechecks exist against a simulated store; they are not connected to real Neo4j writing. | `driver/core/driver_write_cli.py:666–738`; `driver/core/test_driver_write_cli.py` |
| Old growth code supplies year-over-year without quote evidence. | `driver/core/driver_units.py:66–76,162–170`; current rule 3.33 |
| The new number converter multiplies an explicit scale rather than choosing a scale from name or wording. | `driver/core/slot_convert.py:119–177,205–299` |
| A duration with one exact date is held; current evidence-backed completion of the other endpoint is not implemented here. | `driver/core/driver_period_resolver.py:292–303`; current rule 3.42 |
| Calendar lookup can read old Guidance periods and caches, without importing those facts as DriverUpdates. | `driver/core/driver_period_resolver.py:545–552`; `.claude/skills/earnings-orchestrator/scripts/guidance_write_cli.py:125–147` |
| Older preparation corrects the tested wordless beat to in-line; newer conversion does not. | `driver/core/driver_write_cli.py:232–254`; `driver/core/prepared_fact_v2.py:623–649`; current rule 4.10 |
| The filing checker verifies a submitted same-filing candidate. It is not the optional post-save concept-selection/linking service. | `driver/core/xbrl_attach.py:761,1055–1306`; current U2b |
| Record-field matching is test scoring, not the independent Driver meaning check. | `driver/core/fact_match.py:37–141`; current 2.40, 8.2 |
| The history helper trusts an explicit confirmation supplied by its caller; it does not inspect meaning itself. | `driver/core/backfill_seam.py:19–38` |
| The Fiscal AI command still calls the older outside known-value search. | `driver/channels/fiscal_ai/run_code_tier.py:33,245–263`; `scripts/driver_seed/locate.py` |
| New source packing is prepared, but the command still invokes the older builder. | `driver/channels/fiscal_ai/build_packets.py:120–131,174` |
| Current shared search requires tagged filing HTML and supports only dollars, shares and dollars per share. | `driver/relocation/locator.py:928–940,1309–1313`; `driver/relocation/exact_numbers.py:89–97` |
| Old name-string-only matching deliberately refuses all requests after checking their shape. | `driver/relocation/locator.py:761–818` |

### Extra controlled examples

- **Growth:** “Revenue rose 12%,” explicit “year over year,” and “FY2027 revenue growth of 12%” all returned `percent_yoy` through the older unit helper. The explicit year-over-year case is the positive control. Current 3.33 requires the unspecified cases to remain `unknown`. The newer converter retained exact 12 when given `unknown`.
- **Dates:** truly absent period information returns no period. A duration with an end date but no start date is held, even when fiscal year/quarter are present. This shows a safe refusal, not complete current 3.42 support.
- **Birth and surprise:** the paired positive/negative cases are recorded above in “Checks run so far.” No database write was attempted in any probe.

### Test-reading limits

- All 29 code files were read across three parallel code reviews. All 56 test files were inspected for what they exercise; the safe suite was run in full. The three reviewers then separately checked the written guide against their assigned code.
- Some older test names overstate what the current body proves. For example, `test_locator_routes.py` supplies no tagged HTML in several sign/unit/period cases, so they now pass through a blanket unsupported-input refusal. Positive current binding tests are elsewhere (`test_route_a.py`, `test_bind_graph_fact.py`, `test_two_view_bridge.py`). The guide describes the current behavior.
- Several tests depend on saved evidence outside `driver/`. Channel-specific tests also live under `scripts/driver_seed/`: `test_run_code_tier.py`, `test_build_packets.py`, `test_route_a_source.py`, `test_wp3_packet_contract.py`, `test_stage_a_v2.py`. They were located and traced, but this review did not run that additional suite.
- No full launch-quality test of a real reader or independent AI checker was run. No full production write path was activated. These remain outside what the recorded passing counts prove.

## Pass 4 — Review of the explanation

The first draft covered all 92 files and all 19 design homes. Three independent follow-up reviews checked it against the code they had read. The corrections below were applied to the guide:

- Explained “tagged figure” and “slice” once in ordinary words.
- Described the number converter as converting, not saving.
- Narrowed the public-field helper: it checks unexpected fields and incomplete breakdown pairs, not every evidence requirement.
- Said exactly what the history helper trusts: a confirmation supplied by another program, not an independent check inside this helper.
- Removed acceptance from the reason-code module's job; successful acceptance normally has no such reason code.
- Clarified that the XML-name helper checks spelling; it does not resolve the naming authority by itself.
- Made exact reuse the main point of the slice-label helper.
- Removed a false implication that `test_slice_menu.py` tests the public-time cutoff.
- Explained the old Guidance date lookup without suggesting that Guidance facts are imported.
- Qualified period coverage with the missing-endpoint limitation.
- Folded the design-difference table, outside dependencies and test evidence to keep the first view small.

## Pass 5 — Completeness and change check

- A script compared the guide's file links against the original inventory: **92 of 92 covered; none missing**.
- Every linked local file and folder existed.
- Every `driver/` file still matched its original fingerprint after the tests and drafting.
- The categorized rules still matched the starting fingerprint and starting commit. A reviewer's suspicion that the file had shifted during this task was checked and not confirmed.
- Only this scratchpad and `DriversFinal/DRIVER_CODE_GUIDE.md` were authored for this task. Existing code, rules, the workflow scratchpad and Notion were not edited.

The guide explains the current pieces and their limits. It does not certify the entire design, approve old behavior, or propose adding machinery.
