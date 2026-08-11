# Fiscal -> Core V2 Stage-A execution receipt

**Date:** 2026-08-11
**Scope:** frozen plan §9 steps 1–8 only; stop before review step 9
**Result:** staged V2 builder plus both review corrections implemented and
tested; V1 remains live

## 1. Frozen authorities and starting snapshot

```text
HEAD
bd267040c443e85c9275d1621b91ae654d0fd307

approved plan
febf26c05ba2722436e3d66ea0b95f01f8803bba98a911dc13b07df19ec85c14
  .claude/plans/Drivers/WIP/Fiscal_CoreV2_Integration_ReviewPlan_2026-08-11.md

staged contract
d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b
  .claude/plans/Drivers/FinalDesign/ChannelContractV2.md
```

The full pre-existing dirty status contained 917 entries. Its exact
`git status --porcelain=v1 -z` bytes were frozen as:

```text
99d05d4c5e26143f2c4baddf38c6b0cb3f58b88bdc6f3b2cf844c6f13537202b
```

The candidate production files were clean. Relevant pre-existing state was:

```text
 D scripts/driver_seed/relocate_probe/route_a_e2e_150.py
 D scripts/driver_seed/relocate_probe/route_a_e2e_150_result.json
 D scripts/driver_seed/relocate_probe/test_xbrl_gate.py
 D scripts/driver_seed/relocate_probe/xbrl_gate_expected.json
?? .claude/plans/Drivers/WIP/Fiscal_CoreV2_Integration_ReviewPlan_2026-08-11.md
```

None of those owner deletions was restored or changed.

Starting candidate-file hashes:

```text
d1b22707cf397e68aea40146201eff646bd4eb9203bae2af5689dfa5f98de0ce  scripts/driver_seed/build_packets.py
7b3266ab5f4707c73d70399358797841d9a1871c8f0a62262f1f6cf2c28442f2  scripts/driver_seed/public_contract.py
effd9b37450daa796a1c6564a785de17a60877f210125151a05fd4b0df297ebe  scripts/driver_seed/run_code_tier.py
0360627655deb013afa50ea5d51298a778aecbb1b159540032fbd1fb68e66f86  scripts/driver_seed/wp3_compliant_packet.py
```

## 2. Protected artifacts

These 15 hashes were recorded before editing and matched again after the final
test run:

```text
c15f483f06c40aecf3f9bf9008943cc0debe0de811a79c630b1a24c45b0cf5ce  data/driver_catalog_seed/wp1/packets.jsonl
9998705c4bae8e0fb5811c076d99404ece0a2c072dd4d35c93480491e0bcc14c  data/driver_catalog_seed/smoke/packets.jsonl
25a33cb4379fae794be904c39caa9c0b60b2f05c60857f155b46c5ac8693254e  data/driver_catalog_seed/wp3_aci_stream/packets.jsonl
7d8b824de14543b905841581c31a5d776a6d662633fee65ec7e0c879c53d3c9e  data/driver_catalog_seed/wp3_ce_compliant/packets.jsonl
85f6327b04418f6a27f6dc70aa5169559b4c9f146a37aa28b134e2df323d2c11  data/driver_catalog_seed/s4_fixtures/recorded_candidates.jsonl
c15f483f06c40aecf3f9bf9008943cc0debe0de811a79c630b1a24c45b0cf5ce  data/driver_catalog_seed/p4diff/packets.jsonl
c15f483f06c40aecf3f9bf9008943cc0debe0de811a79c630b1a24c45b0cf5ce  data/driver_catalog_seed/p4diff3/packets.jsonl
4feb4c4bf261fd9fb884986b340d23fd0b25664156b9d723c2a9a4bcb48d499a  data/driver_catalog_seed/wp3_aci_dryrun/packets.jsonl
c05747097a9414cbd50dc73acabb79be4d9bedc7aca2eff13515f8f6533373c7  data/driver_catalog_seed/s4_rehearsal/audit/0001306830-24-000155/2026-07-24T003400218926_4e07aa09308a.json
de132d591e83dd6b576e3f5806b34d53fcab0c40e54ec635f30a4041be023f16  data/driver_catalog_seed/s4_rehearsal/audit/0001646972-23-000045/2026-07-24T003410110603_ea7216947564.json
d6ba031f31a63c80c75b11825dc4037592e5b48b7c2b98bc6bcccce3d213fef6  data/driver_catalog_seed/s4_rehearsal/audit/0001646972-23-000056/2026-07-24T003416948494_383bd56b839d.json
b6e5efdfcc28b03aad2f4652bfcc4a1800e2e32011814d02e82d41fa8a3ea7cb  data/driver_catalog_seed/s4_rehearsal/audit/0001646972-24-000165/2026-07-24T003421833580_0f09e155b463.json
67adf82647ca3bc3ff9c097069a9f8d5a6b17025704466a2216639b38510c670  data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-MERGED/2026-07-24T003426845819_82af9373a32b.json
723ce61af1c0f7956c2c7d36347966b33eddd55046b5b4cb1c965bbd353e0978  data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-PARKED/2026-07-24T003426853740_7bc7b008ee3e.json
cd74177cc2d04f506b87fde1028b5a70566ea444007d28e9b438c6c0c0f658ec  data/driver_catalog_seed/s4_rehearsal/audit/SYN-CTRL-REJECTED/2026-07-24T003426860704_9c9787c225ea.json
```

## 3. RED-first proof

Baseline V1 command:

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_build_packets.py \
  scripts/driver_seed/test_wp3_packet_contract.py \
  -q -p no:cacheprovider --no-header --tb=short
```

Raw result before any production edit:

```text
........................                                                 [100%]
24 passed in 6.41s
```

The new test file was then added before behavior changed. Its first run failed
all eight tests because these exact symbols did not exist:

```text
BP._group_events
RC.event_text_parts
PC.convert_dimensions
BP.build_stage_a_v2

8 failed in 4.22s
```

No test failure was removed or weakened. The one mistaken hand-entered
per-source item split was replaced by the live derived counts before GREEN.

## 4. Initial small implementation

Changed production files:

```text
scripts/driver_seed/build_packets.py    +50 -9
scripts/driver_seed/public_contract.py  +22 -14
scripts/driver_seed/route_a_source.py    +7 -0
scripts/driver_seed/run_code_tier.py    +54 -20
```

Added or changed test files:

```text
scripts/driver_seed/test_stage_a_v2.py      new
scripts/driver_seed/test_run_code_tier.py   +17 -0
```

What changed:

1. `_group_events` is now the one grouping owner used by live V1 and staged V2.
2. `_route_abstains` is the one unchanged SKIP/PARK owner used by both paths.
3. V2 emits `raw_label_or_claim` directly and never calls V1 `to_public()`.
4. V2 never calls `unit_hints()`; V1 still does until the later switch.
5. `event_text_parts` copies the source layer's `{part, content}` rows exactly
   once. It never creates position labels, cleans content, searches for scale,
   or infers meaning.
6. `convert_dimensions` is the former V1 dimension code extracted into one
   mechanical owner. Both paths use it; no dimension or `slice_part` rule was
   copied.
7. The V2 field list is derived from the one existing raw field list; a second
   duplicate field list was removed during the simplification pass.
8. Route A now exposes the existing prepared inline-filing representation as
   one stable `inline_html` part. Prose fetchers use each graph node's existing
   `id` as the part label and request `ORDER BY part`; equal content on distinct
   nodes remains distinct.

No Core module is imported. No Fiscal validator or trust-door wrapper exists.

Initial checkpoint file hashes:

```text
50c9bf57d6b7fedc3446d79490214691cc6db704b053d3debf814a109dadd2ca  scripts/driver_seed/build_packets.py
7e853176ff4856ff07bf9e7e1a8537d6e1084ee1cc3dd5bbd2a767c0856c5b51  scripts/driver_seed/public_contract.py
7196932c2395fb588591ddc3119c982451cfa3a74110d52904fb1d7d76fbfd81  scripts/driver_seed/run_code_tier.py
af64b79a8ae027ba2151042cfc6e4b80cac0e012c2baeef72377e939db896b3b  scripts/driver_seed/route_a_source.py
575180664dc38d005896ae85fa73484f6add62762208c022c206df32e833150d  scripts/driver_seed/test_run_code_tier.py
17cd7a977d6126be691118408be340bd221e2e0791a9a97c9cf55476b94284ae  scripts/driver_seed/test_stage_a_v2.py
```

## 5. Exact test commands and results

The outputs in this section preserve the initial step-1-through-8 run. Review
then found two real source-path defects. The corrected final commands and raw
results in §8 supersede the readiness conclusion of this initial run.

### Contract pin

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  driver/core/test_v2_attacks.py -q -p no:cacheprovider \
  --no-header --tb=short -k 'staged_V2_contract'
```

```text
..                                                                       [100%]
2 passed, 64 deselected in 0.10s
```

### Focused V2 plus V1

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_stage_a_v2.py \
  scripts/driver_seed/test_build_packets.py \
  scripts/driver_seed/test_wp3_packet_contract.py \
  -q -p no:cacheprovider --no-header --tb=short
```

```text
................................                                         [100%]
32 passed in 55.56s
```

### Stage-A real-data and population output

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_stage_a_v2.py \
  -q -s -p no:cacheprovider --no-header --tb=short
```

```text
STAGE_A_V1_POPULATION {"artifacts": 7, "by_source_type": {"10k": {"events": 69, "items": 434}, "10q": {"events": 22, "items": 127}, "8k": {"events": 45, "items": 182}}, "packaged": {"events": 136, "items": 743}, "source_replay": {"cache_missing": {"events": 47, "items": 185}, "complete": {"events": 40, "items": 137}, "quote_mismatch": {"events": 49, "items": 421}}}
..
8 passed in 50.17s
```

The same run separately proves all 11 modern CE/ACI Route-A items against their
cached representation hash, quote span, and every nested evidence-piece span.
No skip branch exists in that test.

The 743-item number is structural packaging coverage. The replay split is
reported separately and is not overstated as evidence certification. Old V1
files without the matching cached representation are historical fixture
limitations. Only the 11 modern items are claimed as exact source-evidence
replay in this staged change.

### Live source checks, zero skips

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_run_code_tier.py \
  -q -p no:cacheprovider --no-header --tb=short -rA
```

```text
21 passed, 5 warnings in 50.70s
```

There were no skips. The five warnings are the existing Neo4j driver-destructor
deprecation warning from five live tests; no test failed or skipped.

### Route-A regression, zero skips

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  driver/relocation/test_route_a.py \
  -q -p no:cacheprovider --no-header --tb=short -rA
```

```text
.......................................................                  [100%]
55 passed in 6.57s
```

### Final combined regression after the last edit

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_*.py driver/relocation/test_route_a.py \
  -q -p no:cacheprovider --no-header --tb=short
```

```text
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 66%]
........................................................................ [ 88%]
....................................                                     [100%]
324 passed, 5 warnings in 117.92s (0:01:57)
```

No tests skipped.

### V1 exact parity against frozen HEAD

The command loaded `build_packets.py` directly from commit
`bd267040c443e85c9275d1621b91ae654d0fd307`, ran both old and new V1 builders
over the tracked WP1 inputs, and compared both Python values and serialized
bytes.

```text
V1_WP1_PARITY records 183 abstains 997 packets 37 items 183 bytes 331175 byte_identical True
```

### Static checks

```bash
venv/bin/pyflakes \
  scripts/driver_seed/build_packets.py \
  scripts/driver_seed/public_contract.py \
  scripts/driver_seed/run_code_tier.py \
  scripts/driver_seed/test_stage_a_v2.py

git diff --check -- \
  scripts/driver_seed/build_packets.py \
  scripts/driver_seed/public_contract.py \
  scripts/driver_seed/run_code_tier.py \
  scripts/driver_seed/test_stage_a_v2.py
```

Raw output from both commands was empty; both exited 0.

## 6. Initial dirty-tree isolation proof

At the initial checkpoint, after removing only its four intended Fiscal entries
from the porcelain status, the remaining bytes had the exact baseline hash:

```text
status_entries_now 921
unrelated_status_sha256 99d05d4c5e26143f2c4baddf38c6b0cb3f58b88bdc6f3b2cf844c6f13537202b
baseline_status_sha256  99d05d4c5e26143f2c4baddf38c6b0cb3f58b88bdc6f3b2cf844c6f13537202b

 M scripts/driver_seed/build_packets.py
 M scripts/driver_seed/public_contract.py
 M scripts/driver_seed/run_code_tier.py
?? scripts/driver_seed/test_stage_a_v2.py
```

This receipt itself is a fifth intended untracked review file; it was written
after that code-isolation measurement.

## 7. Explicit holds and next boundary

- V1 is still live and reachable.
- V2 is staged and in-memory only.
- The 15 protected artifacts are unchanged.
- No folder was moved.
- No AI call was made.
- Neo4j was read by the existing live tests; no Neo4j write was made.
- No commit or push was made.
- The V1 -> V2 switch was not started.
- Core's future thin router and post-router integration tests were not built or
  called; they remain Core-owned and are outside §9 steps 1–8.

Stop here for owner review.

## 8. Review-required correction: source-owned parts

### Reproduced defects

The review reopened only plan §9 steps 4 and 8. Before changing production:

- a real `route_a_source.build_source()` object contained XBRL data and inline
  HTML but no Stage-A text part; its four located CE items therefore produced
  an event with `text_parts=[]`;
- the prose bridge created `text:0`, `text:1`, ... from `source['texts']`;
- both live prose fetchers used unordered `collect(DISTINCT content)` and thus
  discarded source-node identity and merged distinct nodes with equal content;
- the Stage-A test copied prepared text into a replacement source object, so it
  never exercised the defect.

The first RED run stopped on the actual missing part:

```text
test_red_exact_contract_shape_and_shared_event_grouping
assert event["text_parts"] == expected_parts
E   AssertionError: assert [] == [{'content': ..., 'part': 'source-node-1'}]
1 failed in 0.33s
```

The other RED tests independently required the absent `_fetch_text_parts`
owner and the absent real Route-A `text_parts` field.

### Small correction

1. `route_a_source.build_source()` calls the existing memoized
   `inline_html.prepare()` owner and exposes its visible representation once as
   `{'part': 'inline_html', 'content': prepared['text']}`. The locator still
   receives its original `inline_html` and `texts=[]`; no locator rule changed.
2. `_fetch_text_parts()` reads each prose node's existing `n.id` and content,
   with `ORDER BY part`. It does not use a position, content-derived identity,
   or `DISTINCT`. Duplicate/missing node IDs fail closed.
3. `fetch_filing()` uses the existing `HAS_SECTION` source set. The 8-K source
   uses the existing `HAS_EXHIBIT`, `HAS_SECTION`, and `HAS_FILING_TEXT` source
   set. Both derive legacy `texts` and Stage-A `text_parts` from the same rows.
   `fetch_corpus()` remains the explicitly frozen benchmark-only tuple fetcher;
   it does not create a Stage-A source event and was intentionally unchanged.
4. The four retired names in the Stage-A tests are parsed directly from
   `ChannelContractV2.md`; no copy remains in that test file.
5. Mutations prove the tests fail for a missing part, reversed parts, any
   contract-declared retired field, and an unconverted dimension bundle.
6. Grouping and dimension conversion were not redesigned or changed during
   this correction.

Neo4j's ordering rule was checked against its official documentation: without
`ORDER BY`, result order is not guaranteed:
https://www.neo4j.com/docs/cypher-manual/25/clauses/order-by/

### Live source-node inventory

Read-only current-graph census over text-bearing report relationships:

```text
SOURCE_PART_CENSUS
ExhibitContent {'rows': 38946, 'with_id': 38946, 'distinct_ids': 38946}
ExtractedSectionContent {'rows': 198641, 'with_id': 198641, 'distinct_ids': 198641}
FilingTextContent {'rows': 2689, 'with_id': 2689, 'distinct_ids': 2689}
missing_ids 0
```

One exploratory read-only query that grouped every full content string reached
Neo4j's per-query memory limit and was stopped. It made no writes and was not
used as evidence. The bounded census above plus the exact live source tests are
the final evidence.

### Corrected focused and real-source results

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  driver/core/test_v2_attacks.py -q -p no:cacheprovider \
  --no-header --tb=short -k 'staged_V2_contract'
```

```text
2 passed, 64 deselected in 0.10s
```

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_stage_a_v2.py \
  scripts/driver_seed/test_build_packets.py \
  scripts/driver_seed/test_wp3_packet_contract.py \
  -q -p no:cacheprovider --no-header --tb=short
```

```text
35 passed in 63.83s (0:01:03)
```

The 11 Stage-A tests include the real
`route_a_source -> locator -> build_stage_a_v2` path. Four CE items and all 11
saved modern CE/ACI items use the actual source object; no test replaces it.

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_run_code_tier.py \
  -q -p no:cacheprovider --no-header --tb=short -rA
```

```text
21 passed, 5 warnings in 52.38s
```

There were zero skips. The five warnings are the pre-existing Neo4j driver
destructor warning. The live ACI/AAPL/WMS 8-K sources and AAPL filing source
all had nonempty, unique, sorted node-ID parts whose content exactly rebuilt
the locator's `texts` list.

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_route_a_source.py \
  scripts/driver_seed/test_wp3_packet_contract.py \
  driver/relocation/test_route_a.py \
  -q -p no:cacheprovider --no-header --tb=short -rA
```

```text
75 passed in 20.19s
```

### Exact reproducible V1 parity command

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python - <<'PY'
import json
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path.cwd()
HERE = ROOT / 'scripts/driver_seed'
sys.path.insert(0, str(HERE))
import build_packets as current

head = 'bd267040c443e85c9275d1621b91ae654d0fd307'
source = subprocess.check_output(
    ['git', 'show', f'{head}:scripts/driver_seed/build_packets.py'], text=True)
old = types.ModuleType('frozen_build_packets')
old.__file__ = f'{head}:scripts/driver_seed/build_packets.py'
exec(compile(source, old.__file__, 'exec'), old.__dict__)

pdir = ROOT / 'data/driver_catalog_seed/wp1'
records = [json.loads(line) for line in (pdir / 'code_resolved.jsonl').read_text().splitlines()]
abstains = [json.loads(line) for line in (pdir / 'abstain.jsonl').read_text().splitlines()]
saved = [json.loads(line) for line in (pdir / 'packets.jsonl').read_text().splitlines()]
fye = {packet['ticker']: packet['fye_month'] for packet in saved}
old_result = old.build(records, abstains, fye)
new_result = current.build(records, abstains, fye)

def tuple_wire(result):
    return json.dumps(result, default=current._exact_default).encode()

def writer_wire(result):
    return b''.join(
        (json.dumps(row, default=current._exact_default) + '\n').encode()
        for group in result for row in group)

old_tuple, new_tuple = tuple_wire(old_result), tuple_wire(new_result)
old_writer, new_writer = writer_wire(old_result), writer_wire(new_result)
print('V1_WP1_PARITY',
      'records', len(records),
      'abstains', len(abstains),
      'packets', len(new_result[0]),
      'items', sum(len(packet['items']) for packet in new_result[0]),
      'tuple_bytes', len(new_tuple),
      'writer_bytes', len(new_writer),
      'byte_identical', (old_result == new_result and old_tuple == new_tuple
                         and old_writer == new_writer))
assert old_result == new_result
assert old_tuple == new_tuple
assert old_writer == new_writer
PY
```

```text
V1_WP1_PARITY records 183 abstains 997 packets 37 items 183 tuple_bytes 331175 writer_bytes 330135 byte_identical True
```

### Corrected full regression and identity checks

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_*.py driver/relocation/test_route_a.py \
  -q -p no:cacheprovider --no-header --tb=short
```

```text
327 passed, 5 warnings in 134.09s (0:02:14)
```

The former 324-test command now contains three new review tests, hence 327.
There were zero skips.

```text
PROTECTED_HASHES 15 of 15 unchanged
STATUS entries 924 intended 7 unrelated 917
UNRELATED_STATUS_SHA256 99d05d4c5e26143f2c4baddf38c6b0cb3f58b88bdc6f3b2cf844c6f13537202b
```

The unrelated-tree hash exactly equals the frozen starting hash. The seven
intended review paths are the four production files, two tests, and this
receipt. The plan hash remains
`febf26c05ba2722436e3d66ea0b95f01f8803bba98a911dc13b07df19ec85c14`;
the contract hash remains
`d8c3af40455376a03c2803f61aae1be92f545a7980880c9a77c4a3c017b3173b`.

`pyflakes` and `git diff --check` both exited 0 with empty output.

### Final hold

V1 remains live. V2 remains staged and in memory. No protected artifact,
folder, Core file, grouping rule, or dimension rule changed. No AI call,
Neo4j write, regeneration, repin, activation, commit, or push occurred. Stop
again for owner review.

## 9. Final deletion-first correction

This section supersedes earlier current-state references to the temporary
`inline_html` part label, the deleted `event_text_parts()` wrapper, earlier file
hashes, and earlier final-run timing. No other design or behavior changed.

### RED proof

Tests were changed before production. Both exact defects failed:

```text
test_red_exact_text_parts_once_without_cleanup_or_guessing
E   AssertionError: assert not True
E    + where True = hasattr(RC, 'event_text_parts')

test_red_real_route_a_source_locator_to_stage_a_has_prepared_part
E   AssertionError: assert 'inline_html' == '0001306830-24-000155'

2 failed, 9 deselected in 2.22s
```

### Deletions and replacement

1. Route A's one prepared part now uses the already-owned accession/source ID
   as `part`. The invented `inline_html` part label is gone. The separate
   locator input field named `inline_html` remains because it is the existing
   locator API, not a Stage-A part label.
2. `run_code_tier.event_text_parts()` was deleted completely.
3. `build_stage_a_v2()` now performs one direct `copy.deepcopy()` of
   `sources_by_id[source_id]['text_parts']`. This preserves the source's label,
   order, content, and ownership without a wrapper or second rule.
4. Tests and the historical replay fixtures now use each event's existing
   source ID. No grouping, dimension, source-selection, matching, or locator
   rule changed.

The two RED tests then passed:

```text
2 passed, 9 deselected in 2.19s
```

### Final reruns

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_stage_a_v2.py \
  scripts/driver_seed/test_build_packets.py \
  scripts/driver_seed/test_wp3_packet_contract.py \
  -q -p no:cacheprovider --no-header --tb=short
```

```text
35 passed in 63.06s (0:01:03)
```

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest \
  scripts/driver_seed/test_*.py driver/relocation/test_route_a.py \
  -q -p no:cacheprovider --no-header --tb=short
```

```text
327 passed, 5 warnings in 133.17s (0:02:13)
```

There were zero skips. The warnings remain the same pre-existing Neo4j driver
destructor warnings.

```text
V1_WP1_PARITY records 183 abstains 997 packets 37 items 183 tuple_bytes 331175 writer_bytes 330135 byte_identical True
PROTECTED_HASHES 15 of 15 unchanged
STATUS entries 924 intended 7 unrelated 917
UNRELATED_STATUS_SHA256 99d05d4c5e26143f2c4baddf38c6b0cb3f58b88bdc6f3b2cf844c6f13537202b
```

Current file hashes:

```text
ca1eacd6ed98c2e943465f1d789b472f7e715dade0607de9982489db23a0cdc6  scripts/driver_seed/build_packets.py
7e853176ff4856ff07bf9e7e1a8537d6e1084ee1cc3dd5bbd2a767c0856c5b51  scripts/driver_seed/public_contract.py
55cfc3f98073f69f099ec5c72c4b6d4304736cbf7169602abc2e64a44c273d66  scripts/driver_seed/run_code_tier.py
33ab79b2dfc8307991e8563af56d34a2803a40188a6ca33fcc30b773dc97f9f9  scripts/driver_seed/route_a_source.py
575180664dc38d005896ae85fa73484f6add62762208c022c206df32e833150d  scripts/driver_seed/test_run_code_tier.py
899fa9a4fd44d948ffd8024dc160b784b399833af6fdf2435136ab16c48b39bc  scripts/driver_seed/test_stage_a_v2.py
```

The frozen plan and contract hashes remain unchanged. `pyflakes` and
`git diff --check` exited 0 with empty output.

### Final hold after deletion-first correction

V1 remains live; V2 remains staged. No AI call, Neo4j write, regeneration,
repin, folder move, activation, commit, or push occurred. Return for final
owner review.
