# Fiscal -> Core V2 staged integration plan

**Status:** review plan only. The read-only inventory is complete. No Fiscal or
Core production code has been changed by this plan.

**Staged authority:**
`.claude/plans/Drivers/FinalDesign/ChannelContractV2.md` at commit
`bd267040c443e85c9275d1621b91ae654d0fd307`.

**Contract SHA-256:**
`d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b`.

**Important:** V2 is staged, not live. `ChannelContract.md` V1 and
`15_CandidateFactPacket.md` V1 remain the live laws until Core performs the
separate atomic V1 -> V2 switch.

## 1. Goal, in plain words

Fiscal should send one raw source event to Core. Core then asks the reader to
understand it, checks it, decides identity and units, and writes it.

```text
Fiscal selects + fetches source
              |
              v
Fiscal sends ONE raw Stage-A event
              |
              v
Core prepares reader input -> checks model/XBRL -> validates -> writes
              |
              v
Fiscal records the final outcome
```

This plan builds and proves Fiscal's Stage-A output while V1 stays live. It
does not activate V2.

## 2. Ownership boundary

### Fiscal owns

- selecting source events;
- fetching exact source evidence;
- sending one Stage-A raw event at a time, in company chronology;
- preserving signed displayed values, quotes, periods, and raw XBRL evidence;
- sending each event's `{part, content}` source text once;
- keeping its own cursor, source-completeness record, and outcome ledger;
- recording Core's final result without renaming it.

### Core owns

- reader-prompt preparation;
- the model trust door;
- the XBRL trust door;
- the one shared production validator;
- driver name, identity, canonical unit, multiplier, and `slice_part`;
- all five final decisions;
- every Driver/DriverUpdate and Neo4j write.

### Fiscal must not add

- a V2 validator;
- a V2 wrapper around either Core trust door;
- a call from Fiscal into `attach_event_xbrl`;
- another unit, scale, name, identity, or outcome rule;
- hardcoded unit words, scale regexes, or copied Core logic;
- a database write.

A future thin event router is allowed, but it is Core-owned.

## 3. Exact staged Stage-A shape

### Event, exactly

```text
source_id
source_type
ticker
fye_month
event_time
text_parts
items
```

The frozen `source_type` values are `8k`, `transcript`, `10q`, `10k`, and
`news`. Fiscal tests cover the source types Fiscal actually emits; they do not
invent a new fetch lane merely to exercise the vocabulary.

`text_parts` is an ordered list. Every entry is exactly:

```json
{"part": "a nonblank source-local label", "content": "exact source text"}
```

The source text is supplied once per event, not copied into a separate event
envelope for every fact. Core's prepared fact later refers to the carried quote
with `part_ref` and, when needed, `occurrence_in_part`.

### Raw item, after retirement, exactly

```text
raw_label_or_claim
value
fmt
is_currency
period_end
cadence
quote
period_evidence
tier
quote_source
xbrl
```

Presence is lane-specific. Optional presence never allows another spelling.

The following four Fiscal-authored fields are forbidden in V2:

```text
level_unit_raw
level_unit_kind_hint
level_money_mode_hint
level_shape_hint
```

`sequential_evidence` is already absent from the Fiscal builder. It is an
absence to keep proving, not code to delete.

### Raw XBRL bundle, exactly

```text
concept
period_start
period_end
ptype
unit
ix
source_evidence
dimensions
```

`ix` is exactly:

```text
scale
sign
format
unit_ref
```

Each public dimension is exactly:

```json
{"axis": "...", "member": "..."}
```

Fiscal never sends `slice_part`. Core derives it later.

### Scale proof

- **Text:** the exact scale wording must be inside the raw item's quote. The
  reader may later copy it as `unit_scale_evidence`. If it is outside, the
  evidence quote must be extended contiguously upstream or the reader abstains.
  Fiscal code does not search for scale words.
- **XBRL:** Stage A carries the raw XBRL bundle. Later
  `unit_scale_evidence` is null. Core proves scale jointly from verified
  `xbrl.ix.scale`, `xbrl.ix.unit_ref`, and bound
  `xbrl.source_evidence.pieces`.

## 4. Current committed shape versus V2

| Area | Current committed Fiscal code | V2 requirement | Planned treatment |
|---|---|---|---|
| Event | six fields; no `text_parts` | seven fields including `text_parts` | staged V2 packager carries exact event parts once |
| Label | builder emits `raw_label`; V1 adapter renames it | `raw_label_or_claim` | V2 packager emits the public spelling directly |
| Unit hints | `unit_hints()` creates four fields | all four forbidden | V2 path never calls it; delete V1 copy at the later switch |
| XBRL dimensions | old records may carry `axis_members`; V1 adapter maps them | exact `{axis, member}` dictionaries | one mechanical transport conversion; never add `slice_part` |
| XBRL evidence | old saved packets vary; the 11 modern items carry the full bundle | exact V2 bundle | preserve the modern Route-A bundle byte-for-byte by value |
| Public adapter | `public_contract.py` is a V1 mapper plus validator | no Fiscal V2 validator/wrapper | do not grow it; V2 packager emits Stage A directly; retire V1 adapter at switch |
| Core call | no single V2 event router exists | future Core-owned router | wait for Core; Fiscal must not call either trust door directly |

There is no tracked live service or scheduler that imports or launches the
current Fiscal packet builder. Its non-test uses are a manual CLI, an audit
fixture builder, and a phase-4 probe. This makes a staged V2 path possible
without activating it.

## 5. Programmatic caller inventory

The inventory was derived from every tracked Python file with `ast`, then
cross-checked with Git text search for direct commands and path strings.

### `build_packets` — 8 import sites

- `driver/relocation/test_route_a.py:567`
- `driver/relocation/test_route_a.py:685`
- `scripts/driver_seed/relocate_probe/phase4/p4_dry_run.py:40`
- `scripts/driver_seed/test_build_packets.py:8`
- `scripts/driver_seed/test_route_a_source.py:67`
- `scripts/driver_seed/test_route_a_source.py:85`
- `scripts/driver_seed/test_route_a_source.py:98`
- `scripts/driver_seed/wp3_compliant_packet.py:19`

It also has its own manual CLI entry point.

### `public_contract` — 4 import sites

- `scripts/driver_seed/test_wp3_packet_contract.py:257`
- `scripts/driver_seed/test_wp3_packet_contract.py:277`
- `scripts/driver_seed/test_wp3_packet_contract.py:302`
- `scripts/driver_seed/wp3_compliant_packet.py:20`

There is no tracked non-audit production caller.

### `route_a_source` — 9 import sites

- `driver/relocation/test_route_a.py:519`
- `driver/relocation/test_route_a.py:538`
- `driver/relocation/test_route_a.py:686`
- `driver/relocation/test_unit_handoff_census.py:84`
- `scripts/driver_seed/test_route_a_source.py:12`
- `scripts/driver_seed/test_wp3_packet_contract.py:147`
- `scripts/driver_seed/test_wp3_packet_contract.py:163`
- `scripts/driver_seed/test_wp3_packet_contract.py:177`
- `scripts/driver_seed/wp3_compliant_packet.py:21`

The earlier plan was wrong to say this should expose a provider interface to
Core. It remains a Fiscal/shared evidence source and a regression surface.
Core owns its filing provider and XBRL trust door.

### `run_code_tier` — 21 import sites

- `data/driver_catalog_seed/wp1_evidence/aci_queries.py:21`
- `data/driver_catalog_seed/wp1_evidence/census_dimension_addresses.py:18`
- `scripts/driver_seed/build_packets.py:15`
- `scripts/driver_seed/fix_quotes.py:15`
- `scripts/driver_seed/recall_report.py:15`
- `scripts/driver_seed/relocate_probe/build_exam_multiaxis.py:8`
- `scripts/driver_seed/relocate_probe/build_multiaxis.py:12`
- `scripts/driver_seed/relocate_probe/build_multiaxis_v2.py:11`
- `scripts/driver_seed/relocate_probe/grade.py:19`
- `scripts/driver_seed/relocate_probe/oracle.py:16`
- `scripts/driver_seed/relocate_probe/phase4/p4_dry_run.py:39`
- `scripts/driver_seed/relocate_probe/phase4/test_p4_dry_run.py:102`
- `scripts/driver_seed/relocate_probe/prep.py:18`
- `scripts/driver_seed/relocate_probe/prep_exam.py:11`
- `scripts/driver_seed/relocate_probe/prep_headline.py:12`
- `scripts/driver_seed/relocate_probe/prep_news.py:17`
- `scripts/driver_seed/relocate_probe/prep_oracle.py:12`
- `scripts/driver_seed/relocate_probe/prep_transcript.py:15`
- `scripts/driver_seed/relocate_probe/test_xbrl_gate.py:68`
- `scripts/driver_seed/test_run_code_tier.py:9`
- `scripts/driver_seed/wp1_verify.py:25`

This broad import surface means its existing public functions should not be
renamed during the contract change. The smallest safe change is additive
transport of event parts, with existing fetch and matching behavior unchanged.
`test_xbrl_gate.py` is tracked at the authority commit but locally deleted in
the owner's dirty working tree. The inventory includes it; Fiscal must not
restore or overwrite that deletion without owner direction.

### `wp3_compliant_packet` — 1 import site

- `scripts/driver_seed/test_wp3_packet_contract.py:82`

It is an audit fixture builder, not the live channel.

## 6. Candidate change surface

This is now called a **candidate surface**, not a confirmed surface. Each file
stays in the list only if its failing test proves it must change.

| Candidate | Why it may change | What must not change |
|---|---|---|
| `scripts/driver_seed/build_packets.py` | owns event grouping and currently creates the four retired hints | source selection, source-completeness routing, exact value serialization |
| `scripts/driver_seed/run_code_tier.py` | already holds each source event's exact text list but drops that event-level list before packet building | all matching, source selection, value checks, and existing function signatures |
| `scripts/driver_seed/public_contract.py` | V1-only adapter; V2 must not use or enlarge it | V1 behavior remains until the staged path is proven; deletion waits for switch |
| `scripts/driver_seed/wp3_compliant_packet.py` | current real-data fixture generator calls the V1 builder and adapter | locator and source evidence behavior |
| tests named in §8 | must pin V2 and V1 non-regression | no synthetic-only replacement for real Route-A proof |
| active artifacts in §7 | inputs to parity tests | no rewrite during staged work |

`route_a_source.py`, the shared locator, and Core files are regression surfaces,
not planned Fiscal edits. If a failing test appears to require changing one,
stop for review rather than expanding the Fiscal patch.

## 7. Tracked retired-hint artifact inventory

### Inventory rule

The command searched the committed Git tree, not untracked working files, under
`data/driver_catalog_seed` for any of the four retired field names.

It finds exactly **15 tracked data artifacts**.

Classification here means:

- **active V1 baseline/fixture:** named by a current test, an authoritative
  baseline manifest, or the current real Route-A regression;
- **historical:** a superseded/determinism copy or a saved rehearsal output.

The old #827 glob census still sees all seven `*/packets.jsonl` files, including
three files classified below as historical. Therefore its old 7-file/743-item
count must not be relabeled as the future active V2 corpus.

### Active V1 baselines/fixtures — 5

| Artifact | Records / items | SHA-256 | Why active |
|---|---:|---|---|
| `data/driver_catalog_seed/wp1/packets.jsonl` | 37 / 183 | `c15f483f06c40aecf3f9bf9008943cc0debe0de811a79c630b1a24c45b0cf5ce` | authorized WP1 baseline, pinned by `wp1_manifest.json` |
| `data/driver_catalog_seed/smoke/packets.jsonl` | 16 / 175 | `9998705c4bae8e0fb5811c076d99404ece0a2c072dd4d35c93480491e0bcc14c` | default input to the committed smoke validator |
| `data/driver_catalog_seed/wp3_aci_stream/packets.jsonl` | 3 / 7 | `25a33cb4379fae794be904c39caa9c0b60b2f05c60857f155b46c5ac8693254e` | current real Route-A/S4 regression input |
| `data/driver_catalog_seed/wp3_ce_compliant/packets.jsonl` | 1 / 4 | `7d8b824de14543b905841581c31a5d776a6d662633fee65ec7e0c879c53d3c9e` | current real Route-A/S4 regression input |
| `data/driver_catalog_seed/s4_fixtures/recorded_candidates.jsonl` | 16 rows | `85f6327b04418f6a27f6dc70aa5169559b4c9f146a37aa28b134e2df323d2c11` | directly hash-pinned and read by `test_s4_rehearsal.py` |

### Historical — 10

| Artifact | Records / items | SHA-256 | Why historical |
|---|---:|---|---|
| `data/driver_catalog_seed/p4diff/packets.jsonl` | 37 / 183 | `c15f483f06c40aecf3f9bf9008943cc0debe0de811a79c630b1a24c45b0cf5ce` | determinism copy of WP1 |
| `data/driver_catalog_seed/p4diff3/packets.jsonl` | 37 / 183 | `c15f483f06c40aecf3f9bf9008943cc0debe0de811a79c630b1a24c45b0cf5ce` | later determinism copy of WP1 |
| `data/driver_catalog_seed/wp3_aci_dryrun/packets.jsonl` | 5 / 8 | `4feb4c4bf261fd9fb884986b340d23fd0b25664156b9d723c2a9a4bcb48d499a` | superseded by `wp3_aci_stream` and has no direct test reader |
| `data/driver_catalog_seed/s4_rehearsal/audit/0001306830-24-000155/2026-07-24T003400218926_4e07aa09308a.json` | 1 output | `c05747097a9414cbd50dc73acabb79be4d9bedc7aca2eff13515f8f6533373c7` | saved V1 rehearsal output; no committed reader |
| `data/driver_catalog_seed/s4_rehearsal/audit/0001646972-23-000045/2026-07-24T003410110603_ea7216947564.json` | 1 output | `de132d591e83dd6b576e3f5806b34d53fcab0c40e54ec635f30a4041be023f16` | saved V1 rehearsal output; no committed reader |
| `data/driver_catalog_seed/s4_rehearsal/audit/0001646972-23-000056/2026-07-24T003416948494_383bd56b839d.json` | 1 output | `d6ba031f31a63c80c75b11825dc4037592e5b48b7c2b98bc6bcccce3d213fef6` | saved V1 rehearsal output; no committed reader |
| `data/driver_catalog_seed/s4_rehearsal/audit/0001646972-24-000165/2026-07-24T003421833580_0f09e155b463.json` | 1 output | `b6e5efdfcc28b03aad2f4652bfcc4a1800e2e32011814d02e82d41fa8a3ea7cb` | saved V1 rehearsal output; no committed reader |
| `data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-MERGED/2026-07-24T003426845819_82af9373a32b.json` | 1 output | `67adf82647ca3bc3ff9c097069a9f8d5a6b17025704466a2216639b38510c670` | saved V1 rehearsal output; no committed reader |
| `data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-PARKED/2026-07-24T003426853740_7bc7b008ee3e.json` | 1 output | `723ce61af1c0f7956c2c7d36347966b33eddd55046b5b4cb1c965bbd353e0978` | saved V1 rehearsal output; no committed reader |
| `data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-REJECTED/2026-07-24T003426860704_9c9787c225ea.json` | 1 output | `cd74177cc2d04f506b87fde1028b5a70566ea444007d28e9b438c6c0c0f658ec` | saved V1 rehearsal output; no committed reader |

### Artifact rule during staged work

- Change none of these 15 files while V1 is live.
- Use the active real items as read-only source inputs and build V2 events in
  memory for the new tests.
- Never rewrite the ten historical items to look current.
- At the later switch, either regenerate an active artifact into a clearly V2
  path or retire its V1 reader. Do not silently reinterpret old bytes.
- Record before/after hashes for every active artifact that eventually moves.

## 8. RED-first tests to add before behavior changes

### A. Contract-shape tests

- Read the `staged_raw_channel` block from the committed V2 contract.
- Assert one event has exactly the seven event fields.
- Assert each text part has exactly `{part, content}`.
- Assert each raw item has only the V2 raw-item spellings.
- Assert all four retired hints are absent.
- Assert `sequential_evidence` remains absent.
- Assert an XBRL dimension has exactly `{axis, member}` and no `slice_part`.
- Assert the raw XBRL bundle and nested `ix` bundle have exact keys.
- Assert no Fiscal production module imports either Core trust door or the Core
  writer.

These are test-time contract comparisons, not a second runtime validator.

### B. Event-part tests

- The source layer's exact parts appear once at event level.
- No item carries its own copy of `text_parts`.
- Content is byte-for-byte the fetched/extracted source string; no cleanup,
  paraphrase, or inferred scale words.
- Part labels are nonblank and stable under two identical builds.
- Two facts from one event reuse one event part list.
- A repeated quote stays lawful; Core's reader later supplies the occurrence.

### C. Text-only path

- A text event carries no XBRL bundle and triggers no XBRL provider/door.
- Signed displayed value, `fmt`, `is_currency`, quote, period evidence, and
  source provenance survive unchanged.
- A fixture whose quote already contains its exact scale wording reaches the
  staged event unchanged.

After Core supplies its thin event router, integration tests also prove:

- A reader answer citing scale wording outside the quote is refused by Core.
- If the source cannot provide a contiguous quote containing required scale
  evidence, the reader abstains; Fiscal code does not guess.
- A text value whose unit remains unclear may reach Core as raw evidence; Core
  decides whether its prepared result is lawful or parked.

### D. XBRL path

- Rebuild all 11 real saved Route-A items in memory into Stage A.
- Preserve signed displayed value, `fmt`, `is_currency`, quote, period, exact
  concept/context fields, unit, `ix`, source evidence, and dimensions.
- Verify each source-evidence hash and span against its cached filing first.
- Assert public dimensions contain only axis/member.

After Core supplies its thin event router, integration tests also prove:

- Assert the later prepared XBRL slot has null `unit_scale_evidence`.
- Prove the real `726` with `ix.scale=6` becomes `726 m_usd` exactly once.
- Prove source row `4,828` under `dollars in millions` becomes
  `4,828 m_usd` exactly once, never `4,828,000,000 m_usd`.
- Wrong scale, unit reference, dimension, source id, representation hash, or
  evidence span fails closed.
- A bad sibling never removes a valid sibling.

### E. Outcomes and safety

After Core supplies its thin event router:

- submit both a text-only and an XBRL-backed event through that one router;
- route every prepared fact through Core's shared validator before any write;
- prove all five public decisions can be recorded exactly:
  `written`, `merged`, `parked`, `skipped`, `rejected`;
- prove only the declared source-unavailable case auto-retries;
- prove no Fiscal code names a Driver or writes to Neo4j;
- run in dry-run mode and assert zero graph writes.

### F. Class-wide population check

- Run every saved Fiscal KPI input shape through the pure Stage-A packager.
- Report exact counts by source type and by accepted/omitted/source-incomplete
  packaging outcome.
- Any new shape becomes an explicit test or a named open item.
- Do not claim this checks AI judgment or live graph writing; those are later
  gates.

## 9. Smallest implementation sequence after this plan is approved

1. **Freeze the working snapshot.** Record HEAD, relevant file hashes, dirty
   paths, and the 15 artifact hashes above.
2. **Add the failing V2 tests.** Keep V1 tests green.
3. **Add one staged Stage-A packager inside the existing builder module.** It
   groups events and transports raw fields. It is not a validator.
4. **Thread exact event parts from the existing source layer.** Do not alter
   matching or infer meaning. Existing source events already hold exact text;
   the new path must carry that list once rather than rebuild it per item.
5. **Emit V2 public spellings directly.** Do not call the V1
   `public_contract.to_public` adapter on the V2 path.
6. **Map raw XBRL dimensions mechanically to `{axis, member}`.** Preserve all
   other raw XBRL values and evidence.
7. **Keep V1 reachable but inactive for Fiscal's staged tests.** V1 remains
   live law until the atomic switch; do not mutate its 15 saved artifacts.
8. **Run focused, real-data, mutation, and full regressions.** No real-data
   skips. Record exact commands and raw output; do not summarize them into an
   unsupported aggregate.
9. **Return for review.** No activation yet.

The temporary V1/V2 coexistence is required only because V1 is still live. At
the switch, remove the V1 Fiscal path, `unit_hints()`, and the obsolete V1
public adapter instead of keeping two implementations.

## 10. Separate change boundaries

### Commit 1 — Fiscal behavior

- staged Stage-A packager;
- exact event-part transport;
- V2 contract tests;
- text and XBRL raw-event parity tests;
- no folder movement;
- no live switch.

The end-to-end router tests land only when Core supplies that router. Fiscal
must not simulate the missing router by calling either trust door directly.

### Commit 2 — folder-only movement

- move the proven live Fiscal-owned import closure to
  `driver/channels/fiscal_ai/`;
- update imports only;
- no logic, data, or expected-output change;
- compare the same test outputs and hashes before and after.

Shared locator, filing extractor, and Core files do not move into the Fiscal
folder. Historical probes and audit outputs remain history.

### Commit 3 — later atomic V1 -> V2 switch

Core owns this switch. It promotes the V2 public contract, separately freezes
the V2 internal packet law, activates the Core router, removes V1 imports and
duplicate paths, and moves the official pins. Fiscal deletes its temporary V1
path in the same reviewed switch boundary.

The Core contract freeze is already its own commit:
`bd267040c443e85c9275d1621b91ae654d0fd307`.

No commit or push is made by this planning step.

## 11. Final gates and paid work

Before activation:

- Core passes independently;
- Fiscal passes independently;
- both text-only and XBRL-backed events pass through the real Core router;
- all relevant real-data tests run with zero skips;
- no graph-write path is enabled during proof;
- the combined regression, lint, deterministic rebuild, and documentation/hash
  checks pass;
- exact commands, commit hash, raw output, and artifact identities are saved.

The ten-call paid pilot is separate from the contract migration. Obtain a
**fresh explicit owner approval immediately before it runs**, even if every
code test is green. Do not reuse an earlier general approval.

The full reader exam, full Fiscal harvest, graph activation, commit, and push
remain outside this plan unless separately authorized.

Qwen/QF-01 is intentionally omitted from this plan.

## 12. Read-only verification receipt for this revision

### Exact command

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  driver/core/test_v2_attacks.py -q -p no:cacheprovider \
  --no-header --tb=short -k 'staged_V2_contract'
```

### Raw output

```text
..                                                                       [100%]
2 passed, 64 deselected in 0.10s
```

### Exact identity commands and raw output

```text
git rev-parse HEAD
bd267040c443e85c9275d1621b91ae654d0fd307

sha256sum .claude/plans/Drivers/FinalDesign/ChannelContractV2.md
d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b

STATUS_AND_HISTORY.md frozen pin
d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b

tracked retired-hint data artifacts under data/driver_catalog_seed
15
```

### Exact artifact-inventory command

```bash
H=bd267040c443e85c9275d1621b91ae654d0fd307
git grep -Il \
  -e 'level_unit_raw' \
  -e 'level_unit_kind_hint' \
  -e 'level_money_mode_hint' \
  -e 'level_shape_hint' \
  "$H" -- data/driver_catalog_seed | sed "s#^$H:##" | sort
```

### Raw artifact paths

```text
data/driver_catalog_seed/p4diff/packets.jsonl
data/driver_catalog_seed/p4diff3/packets.jsonl
data/driver_catalog_seed/s4_fixtures/recorded_candidates.jsonl
data/driver_catalog_seed/s4_rehearsal/audit/0001306830-24-000155/2026-07-24T003400218926_4e07aa09308a.json
data/driver_catalog_seed/s4_rehearsal/audit/0001646972-23-000045/2026-07-24T003410110603_ea7216947564.json
data/driver_catalog_seed/s4_rehearsal/audit/0001646972-23-000056/2026-07-24T003416948494_383bd56b839d.json
data/driver_catalog_seed/s4_rehearsal/audit/0001646972-24-000165/2026-07-24T003421833580_0f09e155b463.json
data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-MERGED/2026-07-24T003426845819_82af9373a32b.json
data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-PARKED/2026-07-24T003426853740_7bc7b008ee3e.json
data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-REJECTED/2026-07-24T003426860704_9c9787c225ea.json
data/driver_catalog_seed/smoke/packets.jsonl
data/driver_catalog_seed/wp1/packets.jsonl
data/driver_catalog_seed/wp3_aci_dryrun/packets.jsonl
data/driver_catalog_seed/wp3_aci_stream/packets.jsonl
data/driver_catalog_seed/wp3_ce_compliant/packets.jsonl
```

The per-artifact record counts, classifications, and full SHA-256 identities
are in §7.

### Exact committed-tree caller-inventory command

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python - <<'PY'
import ast, subprocess
H = 'bd267040c443e85c9275d1621b91ae654d0fd307'
mods = {'build_packets', 'public_contract', 'route_a_source',
        'run_code_tier', 'wp3_compliant_packet'}
paths = [p for p in subprocess.check_output(
    ['git', 'ls-tree', '-r', '--name-only', H], text=True).splitlines()
    if p.endswith('.py')]
for mod in sorted(mods):
    rows = []
    for path in paths:
        try:
            src = subprocess.check_output(
                ['git', 'show', f'{H}:{path}']).decode('utf-8')
            tree = ast.parse(src, path)
        except (UnicodeDecodeError, SyntaxError, subprocess.CalledProcessError):
            continue
        for node in ast.walk(tree):
            hit = (isinstance(node, ast.Import) and
                   any(a.name.split('.')[-1] == mod for a in node.names))
            hit = hit or (isinstance(node, ast.ImportFrom) and
                          (node.module or '').split('.')[-1] == mod)
            if hit:
                rows.append((path, node.lineno))
    print(f'[{mod}] {len(rows)} import sites')
    for path, line in sorted(rows):
        print(f'{path}:{line}')
PY
```

Its raw path/line output is reproduced in §5. The committed-tree scan, unlike
a working-folder scan, includes the owner-deleted but still tracked
`scripts/driver_seed/relocate_probe/test_xbrl_gate.py:68` caller.

The earlier unsupported statement `207 targeted tests and 19 real-data checks
passed` is removed. It is not evidence for this plan.

## 13. Stop conditions

Stop and return to the owner if:

- the staged contract hash moves;
- live Core V2 code disagrees with the staged contract;
- implementation appears to require a Fiscal validator or a direct trust-door
  call;
- a shared locator/Core change appears necessary;
- any of the 15 saved artifacts changes during staged behavior work;
- a real caller outside this inventory appears;
- a required real-data test skips;
- any graph write, AI call, commit, or push would occur without its proper gate.
