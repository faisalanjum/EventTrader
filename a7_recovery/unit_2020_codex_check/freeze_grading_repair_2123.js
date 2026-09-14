// One exact checkpoint inventory; no staging, commit, push or runtime changes.
const fs = require('fs'), path = require('path'), cp = require('child_process');
const crypto = require('crypto'), assert = require('assert/strict');
const ROOT = '/home/faisal/EventMarketDB-driver-recovery';
const A7 = ROOT + '/a7_recovery', HERE = A7 + '/unit_2020_codex_check';
const parent = '86e742ee80321841abd7be9992b826a3abc9e734';
const git = (...args) => cp.execFileSync('git', ['-C', ROOT, ...args],
  {encoding: 'utf8', maxBuffer: 64 * 1024 * 1024});
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
assert.equal(git('rev-parse', 'HEAD').trim(), parent);
assert.equal(git('branch', '--show-current').trim(), 'recovery/a3-a7-verified');
assert.equal(git('diff', '--cached', '--name-only'), '');
const tracked = new Set(git('ls-files', '-z').split('\0'));
const changed = new Set(git('diff', '--name-only', '-z').split('\0').filter(Boolean));
const files = new Map();
function add(p, reason) {
  p = path.resolve(p);
  const rel = path.relative(ROOT, p), stat = fs.lstatSync(p);
  assert(rel.startsWith('a7_recovery/') && !rel.includes('/../'));
  assert(stat.isFile() && !stat.isSymbolicLink(), rel);
  assert(!rel.includes('/unit_2121_current_key/') && !rel.includes('/unit_2123_post_signature_key/'));
  assert.notEqual(rel, 'a7_recovery/grader_20260909/harness_g1v3/build_inventory_review.py');
  assert(!/\.(pyc|strace)$/.test(rel) && !['.env', '.credentials'].includes(path.basename(p)), rel);
  const bytes = fs.readFileSync(p);
  assert(bytes.length < 100 * 1024 * 1024, rel);
  if (files.has(rel)) return;
  files.set(rel, {path: rel, sha256: sha(bytes), bytes: bytes.length,
    git_blob: crypto.createHash('sha1').update(Buffer.from('blob ' + bytes.length + '\0')).update(bytes).digest('hex'),
    state: changed.has(rel) ? 'changed' : tracked.has(rel) ? 'tracked' : 'new', reason});
}
function tree(p, reason, onlyNew = false) {
  for (const e of fs.readdirSync(p, {withFileTypes: true})) {
    if (['__pycache__', '.pytest_cache'].includes(e.name)) continue;
    const child = path.join(p, e.name);
    if (e.isDirectory()) tree(child, reason, onlyNew);
    else if (!onlyNew || !tracked.has(path.relative(ROOT, child))) add(child, reason);
  }
}
for (const name of [
  'a7_grading_input_correction_2114.py', 'a7_grading_revision_2115.py',
  'a7_duplicate_accounting_2116.py', 'test_grading_input_correction_2114.py',
  'test_grading_revision_2115.py', 'test_grading_contract_gaps_2118.py',
  'test_duplicate_accounting_2116.py', 'test_correction_rules_2118.py',
  'prove_grading_input_correction_2114.py', 'prove_duplicate_accounting_2116.py',
  'trace_actual_scoring_2112.py', 'prove_key_grading_reuse_2123.py',
  'INDEPENDENT_INPUT_CHECK_2122.json', 'INPUT_CHECK_AND_RUN_COMMANDS_2122.txt',
  'KEY_REUSE_COMMAND_2123.txt', 'EMPTY_MATCH_POPULATION_2122_RED.txt',
  'CONTRACT_GAPS_2118_RED.txt', 'CONTRACT_2119_HISTORICAL_RED.txt',
  'G3_MATCHED_COMPARATOR_REVIEW_2119.md', 'CORRECTION_SCOPE_DIAGNOSTIC_2119.json',
  'CORRECTION_SCOPE_DIAGNOSTIC_2119_COMMAND.txt',
  'A7_CAUSE_REVIEW_2113.md', 'A7_CAUSE_REVIEW_2114.md', 'A7_CAUSE_REVIEW_2118.md',
  'SOURCE_DISPOSITION_INVENTORY_2118.json', 'GRADING_REPAIR_REVIEW_2123.md',
  'A7_GRADING_FINAL_REVIEW_2105.md', 'freeze_grading_repair_2123.js',
]) add(HERE + '/' + name, 'current code, test, exact proof or bounded review');
add(A7 + '/A7_PREGRADING_WORK_ORDER.md', 'current status, including explicitly open key work');
for (const rel of [
  'unit_2118_correction_native/a7_correction_candidate_2118.py',
  'unit_2118_correction_native/test_correction_native_2118.py',
  'unit_2119_correction_finish/test_correction_mutations_2119.py',
  'unit_2122_sparse_match_groups/payload_sparse_2122.py',
]) add(A7 + '/' + rel, 'actual preparation or native proof dependency');
for (const rel of ['codex_inputfit2119_a', 'codex_inputfit2122_a',
  'codex_counter2116_b', 'codex_scoretrace2112_a', 'codex_keyreuse2123_a',
  'core2122_snapshots', 'codex_contract2119_snapshots', 'codex_corrections2116'])
  tree(HERE + '/' + rel, 'exact real proof, raw inputs or explicitly historical version');
for (const [unit, tags] of [
  ['unit_1957', ['codex_core2122_a', 'core2121_reg_native', 'core2121_reg_ord']],
  ['unit_1947', ['codex_inputfit2122_a', 'codex_keyreuse2123_a', 'codex_counter2116_b']],
]) for (const tag of tags) tree(A7 + '/' + unit + '/logs/attempt_' + tag, 'raw test output and terminal attempt record');
// Include actual read-only test dependencies absent from earlier commits.
// A directory mentioned by a map does not put its members into Git.
for (const name of ['map_core2122_review.tsv', 'map_g23_transport_2103.tsv']) {
  add(HERE + '/' + name, 'exact reviewed execution binding');
  for (const line of fs.readFileSync(HERE + '/' + name, 'utf8').trim().split('\n')) {
    const [, source, digest, mode] = line.split('\t');
    if (mode !== 'ro' || !source.startsWith(ROOT + '/')) continue;
    if (fs.statSync(source).isDirectory()) tree(source, 'unpublished read-only mapped test dependency', true);
    else {
      assert.equal(sha(fs.readFileSync(source)), digest, source);
      if (!tracked.has(path.relative(ROOT, source))) add(source, 'unpublished read-only mapped dependency');
    }
  }
}
for (const rel of ['unit_1957/logs/life_native5/candidate_owed_002',
                   'unit_1893/logs/attempt_reh3/TEST_replies'])
  tree(A7 + '/' + rel, 'existing native test runner dependency', true);
const rows = [...files.values()].sort((a, b) => a.path.localeCompare(b.path));
const report = {status: 'VERIFIED_GRADING_REPAIR_NOT_FINAL_A7_SCORE', parent,
  branch: 'recovery/a3-a7-verified', focused_passes: 85, native_passes: 38,
  historical_regression_passes: 698, historical_skips: 2, new_model_calls: 0,
  scope: 'Grading input, bounded replacement and counter repairs; old-context reuse proof only',
  excluded: ['unverified current-key/post-signature candidates', 'unrelated user work',
             'all unselected artifacts; retained on disk'],
  files: rows, publication_files: rows.filter(r => r.state !== 'tracked').length,
  publication_bytes: rows.filter(r => r.state !== 'tracked').reduce((s, r) => s + r.bytes, 0)};
const output = HERE + '/GRADING_REPAIR_PUBLICATION_2123.json';
fs.writeFileSync(output, JSON.stringify(report, null, 1) + '\n', {flag: 'wx'});
console.log(JSON.stringify({manifest: output, sha256: sha(fs.readFileSync(output)),
  files: rows.length, publication_files: report.publication_files,
  publication_bytes: report.publication_bytes}));
