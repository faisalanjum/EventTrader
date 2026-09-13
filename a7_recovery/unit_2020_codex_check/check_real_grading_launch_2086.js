// TEST ONLY: inspect every real prompt; execute the exact first launch script
// with a local stub, NEVER a model. No artifact in the real run is written.
const fs = require('fs');
const crypto = require('crypto');
const assert = require('assert/strict');
const path = require('path');
const A7 = '/home/faisal/EventMarketDB-driver-recovery/a7_recovery';
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const sha = x => crypto.createHash('sha256').update(x).digest('hex');
const launchPath = A7 + '/unit_2086_real_grading/LAUNCH.json';
assert.equal(sha(fs.readFileSync(launchPath)), '3754473566bf0d8effc043ee3489afb27cc6c5f6fad133f13dc371a0f1a9ef45');
const launch = read(launchPath);
const candidate = read(launch.candidate_dir + '/a7_g1_candidate.json');
const invocation = read(launch.invocation_path);
const script = fs.readFileSync(invocation.scriptPath, 'utf8');
assert.equal(sha(script), launch.first_script_sha256);
assert.equal(sha(fs.readFileSync(launch.invocation_path)), launch.invocation_sha256);
const byBatch = new Map(candidate.batch_rows.map(r => [r.batch_id, r]));
let questions = 0;
const allQuestionIds = new Set();
for (const row of candidate.batch_rows) {
  const prompt = fs.readFileSync(path.join(launch.candidate_dir, row.prompt_path), 'utf8');
  assert.equal(sha(prompt), row.prompt_sha256);
  const marker = '\n[EVENT]\n';
  const at = prompt.indexOf(marker);
  assert(at >= 0);
  const body = JSON.parse(prompt.slice(at + marker.length));
  assert.deepEqual(Object.keys(body).sort(), ['produced_records', 'questions']);
  assert.equal(body.questions.length, row.items);
  assert.deepEqual(body.questions.map(q => q.question_id), row.question_ids);
  assert.deepEqual(body.produced_records.map(p => p.produced_idx), row.produced_idxs);
  for (const q of body.questions) {
    assert.deepEqual(Object.keys(q).sort(), ['question_id', 'reference_card']);
    assert.deepEqual(Object.keys(q.reference_card).sort(), ['quote', 'reference_name', 'values']);
    assert(q.reference_card.quote.includes(q.reference_card.reference_name));
    assert(!allQuestionIds.has(q.question_id));
    allQuestionIds.add(q.question_id);
    questions++;
  }
}
assert.equal(questions, candidate.questions);
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
assert.equal(script.split('export const meta').length, 2);
const run = new AsyncFunction('args', 'agent', 'log', script.replace('export const meta', 'const meta'));
async function exercise(rows, rejected) {
  const seen = [];
  const agent = async (prompt, options) => {
    const r = invocation.args[seen.length];
    const batch = byBatch.get(r.batch_id);
    assert.equal(prompt, fs.readFileSync(path.join(launch.candidate_dir, batch.prompt_path), 'utf8'));
    assert.equal(options.label, r.lane_id);
    assert.equal(options.model, launch.lane.model);
    assert.equal(options.effort, launch.lane.effort);
    assert.equal(options.agentType, launch.lane.agentType);
    assert.deepEqual(options.disallowedTools, launch.lane.disallowedTools);
    seen.push(r.lane_id);
    return 'TEST_ONLY_NOT_A_MODEL_REPLY';
  };
  if (rejected) {
    await assert.rejects(() => run(rows, agent, () => {}));
    assert.equal(seen.length, 0);
  } else {
    const result = await run(rows, agent, () => {});
    assert.equal(result.calls, invocation.args.length);
    assert.deepEqual(seen, invocation.args.map(r => r.lane_id));
  }
}
(async () => {
  await exercise(structuredClone(invocation.args), false);
  const mutations = [
    rows => { rows[0].model = 'TEST_WRONG_MODEL'; },
    rows => { rows[0].prompt_sha256 = '0'.repeat(64); },
    rows => { rows[0].candidate_sha256 = '0'.repeat(64); },
    rows => { rows[0].attempt = 2; },
    rows => { rows[0].prompt = 'TEST_UNAPPROVED_INPUT'; },
    rows => { [rows[0], rows[1]] = [rows[1], rows[0]]; },
    rows => { rows.pop(); },
  ];
  for (const mutate of mutations) {
    const rows = structuredClone(invocation.args);
    mutate(rows);
    await exercise(rows, true);
    await exercise(structuredClone(invocation.args), false);
  }
  console.log(JSON.stringify({kind: 'TEST ONLY; exact real script, local stub, zero model calls',
    prompts: candidate.batch_rows.length, questions, exactFirstSegmentRows: invocation.args.length,
    mutationRefusals: mutations.length, positiveControls: mutations.length + 1,
    realRunWrites: 0}));
})().catch(error => { console.error(error); process.exitCode = 1; });
