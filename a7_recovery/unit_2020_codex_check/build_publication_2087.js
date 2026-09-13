// One checkpoint inventory, not a new publication framework. Read the frozen
// Core proposal, account for its omitted dependencies, then hash exact files.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const cp = require('child_process'), assert = require('assert/strict');
const REC = '/home/faisal/EventMarketDB-driver-recovery';
const A7 = REC + '/a7_recovery';
const sha = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const git = args => cp.execFileSync('git', ['-C', REC, ...args], {encoding:'utf8', maxBuffer:32*1024*1024});
const base = A7 + '/unit_2086_publication_inventory/PUBLICATION_2086.json';
assert.equal(sha(base), '7489b0c1fff06173a8deb8b6ac5a0a25fb62672534f38b8e92b45e34f061768f');
const proposal = JSON.parse(fs.readFileSync(base));
assert.equal(git(['rev-parse','HEAD']).trim(), proposal.base_recovery_head);
assert.equal(git(['diff','--cached','--name-only']), '');
const tracked = new Set(git(['ls-files','-z']).split('\0'));
const changed = new Set(git(['diff','--name-only','-z']).split('\0').filter(Boolean));
const excluded = 'a7_recovery/grader_20260909/harness_g1v3/build_inventory_review.py';
const files = new Map(), mapped = new Set();
function add(p, why) {
  p = path.resolve(p);
  const rel = path.relative(REC,p);
  assert(!rel.startsWith('../') && rel !== '' && rel !== excluded, 'out-of-scope '+rel);
  assert(fs.statSync(p).isFile(), 'not a file '+rel);
  if (files.has(rel)) return;
  const bytes = fs.statSync(p).size;
  assert(bytes < 100*1024*1024, 'oversized '+rel);
  files.set(rel,{path:rel,sha256:sha(p),bytes,
    state:changed.has(rel)?'changed':tracked.has(rel)?'tracked':'new',why});
}
function tree(p, why, onlyUnpublished=false) {
  assert(fs.statSync(p).isDirectory());
  for (const e of fs.readdirSync(p,{withFileTypes:true})) {
    if (e.name === '__pycache__' || e.name === '.pytest_cache') continue;
    const f = path.join(p,e.name);
    if(e.isDirectory()) tree(f,why,onlyUnpublished);
    else if(e.isFile()) {
      const r=path.relative(REC,f);
      if(!onlyUnpublished||!tracked.has(r)||changed.has(r)) add(f,why);
      if(onlyUnpublished) mapped.add(r);
    }
  }
}
for (const f of proposal.files) {
  assert.equal(sha(path.join(REC,f.path)), f.sha256, 'proposal drift '+f.path);
  add(path.join(REC,f.path),f.why);
}
// A directory's hash does not put its untracked members into Git.
const map = A7+'/unit_2020_codex_check/map_real_grading_2088.tsv';
add(map,'the exact successful real grading map');
for(const line of fs.readFileSync(map,'utf8').trimEnd().split('\n')) {
  const [,source,,mode]=line.split('\t');
  assert(['ro','rw'].includes(mode));
  if(mode==='rw') continue; // historical closure container; selected phase files are explicit
  if(!source.startsWith(REC+'/')) continue; // live main authority, not copied
  if(fs.statSync(source).isDirectory()) tree(source,'unpublished member of a verified mapped tree',true);
  else {mapped.add(path.relative(REC,source));if(!tracked.has(path.relative(REC,source)))add(source,'verified mapped file');}
}
// These small actual carriers are read by the source/recovery connection.
for(const r of ['unit_2035_input_bound_resume/key_package_2035',
                'unit_2053_owner_retry/recovery_v2']) tree(A7+'/'+r,'actual saved input/recovery carrier');
// Preserve the native evidence already collected for the exact source phases,
// not the whole external native store or generated TEST projects.
for(const unit of ['unit_2029_correction_packet','unit_2035_input_bound_resume',
                  'unit_2053_owner_retry','unit_2056_decision_packet',
                  'unit_2062_settlement_packet','unit_2066_closeout_collection',
                  'unit_2070_targeted_collection','unit_2074_successor_collection',
                  'unit_2080_source_collection']) {
  tree(A7+'/'+unit+'/evidence','retained native/raw evidence of a selected real source phase');
  for(const f of fs.readdirSync(A7+'/'+unit)) if(/^LAUNCH_RECORD_\d+\.json$/.test(f))
    add(A7+'/'+unit+'/'+f,'the frozen authority and identities for that source collection');
}
// Exact passed proofs and their raw output, with failed attempts retained as
// disclosed history. No large TEST/export clone is selected by directory.
const proofFiles = [
  'unit_2020_codex_check/check_saved_chain_2078.py',
  'unit_2020_codex_check/check_chain_packet_2078.py',
  'unit_2020_codex_check/run_chain_regression_2078.py',
  'unit_2020_codex_check/check_chain_native_ids_2078.py',
  'unit_2020_codex_check/consumer_chain_2078.py',
  'unit_2020_codex_check/verify_real_candidate_2082.py',
  'unit_2020_codex_check/prove_real_signer_2084.py',
  'unit_2020_codex_check/lock_real_key_2084.py',
  'unit_2020_codex_check/prepare_real_grading_2085.py',
  'unit_2020_codex_check/freeze_grading_launch_2086.py',
  'unit_2020_codex_check/check_real_grading_launch_2086.js',
  'unit_2020_codex_check/run_grading_2086.py',
  'unit_2020_codex_check/freeze_grading_transport_2088.py',
  'unit_2020_codex_check/map_real_grading_2088.tsv',
  'unit_2087_grading_review/verify_launch_2087.py',
  'unit_2087_grading_review/REVIEW_2087.json',
  'unit_2020_codex_check/build_publication_2087.js',
  'unit_2020_codex_check/GRADING_PREPARATION_REVIEW_2086.md',
  'unit_2020_codex_check/map_real_grading_2085.tsv',
  'unit_2020_codex_check/map_real_grading_2086.tsv',
  'unit_2072_two_event_closeout/test_v6_successor_2072.py',
  'unit_2076_latest_source_decisions/fixture_third_2078.py',
  'unit_2086_publication_inventory/PUBLICATION_2086.json',
  'A7_PREGRADING_WORK_ORDER.md'];
for(const f of proofFiles) add(A7+'/'+f,'current preparation, its proved caller or explicit verification evidence');
const attempts=['codex_chain2078_a','codex_coldchain2078_a','codex_coldchain2078_b',
 'codex_regchain2078_a','codex_fixchain2079_a','codex_ids2080_a','codex_cons2080_a',
 'codex_thirdproof2081_a','codex_thirdfinish2081_a','codex_cand2082_a','codex_candcold2082_a',
 'codex_signproof2084_a','codex_signproof2084_b','codex_lock2084_a','codex_lockcold2084_a',
 'codex_gprep2085_a','codex_gprep2085_b','codex_gprep2086_a','codex_gprepcold2086_a','codex_glaunch2086_a',
 'codex_goperator2087_a','codex_gtransport2088_a','codex_goperator2088_a','codex_goperator2088_b'];
for(const t of attempts) tree(A7+'/unit_1947/logs/attempt_'+t,'raw verification output and attempt ownership/exit');
for(const d of ['unit_2020_codex_check/codex_gprep2086_a',
               'unit_2020_codex_check/codex_gprepcold2086_a',
               'unit_2086_real_grading', 'unit_2088_real_grading']) tree(A7+'/'+d,'verified frozen real preparation; no AI calls yet');
// A file explicitly named by a selected evidence JSON is a dependency even
// when it was missed by a top-level phase list. Never follow broad directories.
const visited=new Set();
function linked(x) {
  if(typeof x==='string' && x.startsWith(REC+'/') && fs.existsSync(x) && fs.statSync(x).isFile()) {
    const rel=path.relative(REC,x);
    if(!tracked.has(rel)||changed.has(rel))add(x,'exact file named by a selected evidence document');
  } else if(x && typeof x==='object') Object.values(x).forEach(linked);
}
while(true) {
  const pending=[...files.keys()].filter(p=>p.endsWith('.json')
    && !p.includes('/raw/') && !p.endsWith('.raw.json') && !visited.has(p));
  if(!pending.length)break;
  for(const p of pending){visited.add(p);linked(JSON.parse(fs.readFileSync(REC+'/'+p)));}
}
for(const p of changed) assert(p===excluded||files.has(p),'unaccounted tracked change '+p);
for(const p of mapped) assert(tracked.has(p)||files.has(p),'missing mapped member '+p);
const rows=[...files.values()].sort((a,b)=>a.path.localeCompare(b.path));
const publish=rows.filter(r=>r.state!=='tracked');
const doc={kind:'Exact verified-preparation checkpoint inventory; not an A7 score',
  base_head:proposal.base_recovery_head, proposal_sha256:sha(base), map_sha256:sha(map),
  counts:{files:rows.length,new:rows.filter(r=>r.state==='new').length,
    changed:rows.filter(r=>r.state==='changed').length,tracked_unchanged:rows.filter(r=>r.state==='tracked').length,
    bytes:rows.reduce((n,r)=>n+r.bytes,0),publication_files:publish.length,
    publication_bytes:publish.reduce((n,r)=>n+r.bytes,0),mapped_members_accounted:mapped.size},
  exclusions:[{path:excluded,reason:'pre-existing unrelated user edit; preserve unstaged'},
    {path:'other unselected scratch and generated TEST/native/export trees',reason:'not selected by a live dependency; preserve on disk'}],
  largest:publish.slice().sort((a,b)=>b.bytes-a.bytes).slice(0,3),files:rows};
const out=process.argv[2];assert(out&&path.resolve(out).startsWith(A7+'/unit_2020_codex_check/'));
fs.writeFileSync(out,JSON.stringify(doc,null,1)+'\n',{flag:'wx'});
console.log(JSON.stringify({manifest:out,sha256:sha(out),counts:doc.counts,largest:doc.largest},null,1));
