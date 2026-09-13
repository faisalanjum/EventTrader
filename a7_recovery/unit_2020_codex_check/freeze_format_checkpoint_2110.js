// Freeze only this verified A7 increment. This script stages or commits nothing.
const fs = require('fs'), path = require('path'), crypto = require('crypto'), cp = require('child_process');
const REC = '/home/faisal/EventMarketDB-driver-recovery';
process.chdir(REC);
const head = cp.execFileSync('git', ['rev-parse', 'HEAD'], {encoding:'utf8'}).trim();
if (head !== 'fd4c9cba54ff1ccbcab2e7c1f2b7597fa5603056') throw Error('checkpoint parent moved');
if (cp.execFileSync('git', ['diff', '--cached', '--name-only'], {encoding:'utf8'}).trim()) throw Error('index not empty');
const U = 'a7_recovery/unit_2020_codex_check/';
const selected = [
 'a7_recovery/A7_PREGRADING_WORK_ORDER.md',
 'a7_recovery/grader_20260909/harness_g1v3/test_a7_trace_1471.py',
 ...[
 'A7_GRADING_FINAL_REVIEW_2105.md','A7_MEANING_FORMAT_RULE_2105.md',
 'a7_meaning_format_2105.py','test_meaning_format_2105.py','test_meaning_format_native_2105.py',
 'mutate_meaning_format_2106.py','meaning_retry_plan_2107.py','test_meaning_retry_plan_2107.py',
 'test_meaning_retry_plan_native_2107.py','check_retry_plan_2107.py','mutate_retry_plan_2107.py',
 'test_advance_retry_connection_2107.py','review_finalized_grading_2104.py',
 'review_g3_completion_2106.py','review_meaning_format_2105.py','review_unused_retry_2107.py',
 'review_unused_retry_2108.py','verify_unused_retry_2109.py','verify_applied_closure_2110.py',
 'ACTUAL_UNUSED_RETRY_CLOSURE_2110.json','map_formatreg_trace_2106.tsv',
 'freeze_format_checkpoint_2110.js',
 'codex_formatmut2106_a','codex_formatnative2105_c',
 'codex_formatreal2105_a','codex_formatreal2107_a',
 'codex_g2seg1review2104_a','codex_g2seg1to4review2105_a',
 'codex_g3completion2106_a','codex_g3native2106_a',
 'codex_operatorretry2107_green','codex_retrymut2107_a',
 'codex_retryplan2107_owner_replay','codex_unusedcounter2107_a',
 'codex_unusedreview2108_a','codex_unusedfinal2109_a','codex_appliedclosure2110_a'
 ].map(x=>U+x),
 ...['advance_2104.sh','rows_left_2104.py','materialize_segment_2104.py',
 'record_workflow_2104.py','launch_note_2104.py','preserve_native_2104.py',
 'known_defect_2105.py'].map(x=>'a7_recovery/unit_2103_execution_prep/'+x),
 'a7_recovery/unit_2103_g23_grading/G2','a7_recovery/unit_2103_g23_grading/G3',
 ...['a7_unused_retry_closure_2106.py','test_unused_retry_2106.py',
 'close_g2_seg05_caller_2108.py','testruns_codex2109_review'].map(x=>'a7_recovery/unit_2106_unused_retry/'+x),
 ...['test_rows_left_2109.py','runs_q1','runs_codex2110_final'].map(x=>'a7_recovery/unit_2109_rowsleft_check/'+x)
];
const logPattern = /^attempt_(codex_(format|retry|unused|g2seg.*review|g3.*2106|operatorretry|rowsleft2110|actualclosure2110|appliedclosure2110)|core21(0[4-9]|10))/;
for (const d of fs.readdirSync('a7_recovery/unit_1947/logs')) {
 if (logPattern.test(d)) for (const file of ['owner.tsv','exit','stdout.txt','stderr.txt']) {
  const p='a7_recovery/unit_1947/logs/'+d+'/'+file;
  if (fs.existsSync(p)) selected.push(p);
 }
}
for (const tag of ['grader_formatnative2105','grader_formatordinary2105',
 'grader_traceisolation2106_a','grader_traceisolation2106_b','grader_formatnative2106_fixed']) {
 for (const file of ['owner.tsv','exit','stdout.txt','stderr.txt']) {
  const p='a7_recovery/unit_1957/logs/attempt_'+tag+'/'+file;
  if (fs.existsSync(p)) selected.push(p);
 }
}
const files = new Map();
function visit(p) {
 const stat=fs.lstatSync(p);
 if (stat.isDirectory()) for (const child of fs.readdirSync(p)) visit(path.join(p,child));
 else {
  if (!stat.isFile()) throw Error('not a regular file: '+p);
  const b=fs.readFileSync(p);
  if (b.length>=100*1024*1024) throw Error('oversized publication blob: '+p);
  const sha=crypto.createHash('sha256').update(b).digest('hex');
  const blob=crypto.createHash('sha1').update(Buffer.from('blob '+b.length+'\0')).update(b).digest('hex');
  files.set(p,{path:p,sha256:sha,bytes:b.length,git_blob_sha1:blob});
 }
}
for(const p of selected) visit(p);
const expected = {
 [U+'a7_meaning_format_2105.py']:'7aeabc6b236d425de3fed02c250f1cf3744296107015d273fb2c395e8fa680f8',
 [U+'meaning_retry_plan_2107.py']:'127bd6c0d41a961476cffb8a7731f6c9dc2355b385dee7de06332347e17c7f94',
 ['a7_recovery/unit_2106_unused_retry/a7_unused_retry_closure_2106.py']:'e72647b3a0d3f5a4ffddd7752ff18dd32229cf87dfea540141cc4189f3a96998',
 ['a7_recovery/unit_2103_execution_prep/rows_left_2104.py']:'c3aa3a99756fc75d6de5806ef0f4f9aad3981ebe4b0a6c7ffc96b1bb4636bccd',
 [U+'codex_appliedclosure2110_a/REVIEW.json']:'6703734b3099796bb0e96ae52f3c78e8026e65716837531aaf025a31f6aa214c',
 ['a7_recovery/unit_1957/logs/attempt_grader_formatnative2106_fixed/stdout.txt']:'4983cf3b0523eabf40ae9fd9762dfab138fe1390686c2c67407d0c8bc2c91368',
 ['a7_recovery/unit_1957/logs/attempt_grader_formatordinary2105/stdout.txt']:'b4494ec120e3ea01a7bb0703e88183f6138b5e9c217745c1c2837259c9d826b0'
};
for(const [p,sha] of Object.entries(expected)) if(files.get(p)?.sha256!==sha) throw Error('review pin moved or absent: '+p);
const rows=[...files.values()].sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);
const out=U+'G2_FORMAT_PUBLICATION_2110.json';
const document={
 status:'VERIFIED_PREPARATION_AND_G3_COLLECTION_NOT_A7_PASS',
 parent:head, branch:'recovery/a3-a7-verified',
 scope:'Exact scalar recovery, existing retry/state owners, verified zero-call closure, saved G2/G3 evidence; no new AI, main, DB or production change.',
 checks:{format_focused:68,retry_focused:14,closure_replayed:51,remaining_count:14,
         format_mutations_caught:12,retry_mutations_caught:6,closure_mutations_caught:3,
         full_affected_regression_passed:698,named_historical_skips:2,
         native_recovered_TEST_readings:139,native_exact_event_leg_routes:99,
         real_G3_calls:33,real_G3_usable_readings:32,real_G3_questions:117,
         real_G3_agreed:110,real_G3_unresolved:7,
         real_G2_calls:4,real_G2_original_valid:1,real_G2_recovered_attempts:3,
         real_G2_remaining_primaries:137,actual_zero_call_closure:true},
 limitations:['A7 has no final score yet;137 G2 primary readings remain.',
 'Existing wrong judgments, unknowns, disagreements, duplicates and G1 gap remain findings, not code repairs.',
 'TEST outputs are labelled synthetic; they do not supply actual model judgments.',
 'Two historical regression skips are documented in the final-review checklist.',
 'Unrelated untracked work and dirty build_inventory_review.py are excluded and untouched.',
 'Earlier red/counterexample logs are failure history, not passing candidates.'],
 file_count:rows.length, bytes:rows.reduce((n,r)=>n+r.bytes,0),files:rows
};
fs.writeFileSync(out,JSON.stringify(document,null,2)+'\n',{flag:'wx'});
process.stdout.write(JSON.stringify({manifest:out,files:rows.length,MiB:(document.bytes/1048576).toFixed(1),
 sha256:crypto.createHash('sha256').update(fs.readFileSync(out)).digest('hex')})+'\n');
