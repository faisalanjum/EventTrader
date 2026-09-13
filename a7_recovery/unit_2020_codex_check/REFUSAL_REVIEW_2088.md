# G1 first launch — verified permission refusal, not a grading result

2026-09-12 Eastern. Core2089 message/archive482e0d22ead929eec6488467b0f294e528546b53f64965acd7ad29de26d5749f
answers exact Codex2088 8c3554135454995e0d89d64c74953a796397abaf06832eaf2bf2c61b52db3e93.
Both sessions and main HEAD are unchanged. Preparation commit467c5de71e0a4e362c26927a8984c97cf713dee3
was pushed and independently confirmed remotely before the launch.

Workflow wf_61f6147b-947 started2026-09-13T02:31:38.916Z (10:31:38 p.m.
Eastern), duration30433ms. Codex independently read the original state and
compared its saved scriptPath, full script bytes and ALL52 ordered arguments
to the published invocation. All match. The durable state equals the original.

First workflow_agent row G1-000/G1a: state=error, blocked=true, no agentId,
error="[G1-000/G1a] blocked by safety classifier: Blocked by classifier".
The journal has one failed entry with empty agentId; its durable copy also
equals the original. There is no worker transcript. Official grading-worker
totals are0 tokens/0 tools. The one returned placeholder has text=null AND
error=null: it is NOT an answer, valid grader reply or meaningful verdict.

| Population | Observed outcome |
|---|---|
| First52 scheduled |1 pre-worker refusal;51 never attempted |
| Model answers / valid grading results |0 /0 |
| Full G1 requirement |192 primary readings, all still unanswered |
| Earlier work |668 retained calls; all382 saved answers unchanged |

The dispatch refusal is separately counted, never dropped because it used no
grading-worker tokens. No recall or A7 PASS/FAIL score is available.

## Exact evidence

Under unit_2088_real_grading:

* LAUNCH_RECORD_SEG01.json83f65e2ea37e97c86fe709da90a7254397745f5f9c3248f830fce4d5154d2465.
* LAUNCHED_SEG01.jsondce013f89460ee3b504a1f4f9c62b7910fc10f9b970ca2713b9d75073edfb275.
* native/seg01/wf_61f6147b-947.state.json e9c9c848c8c5828d68710250ca3e998f4120407b19529fdd8cfdcdc0183f6add,602930bytes.
* native/seg01/wf_61f6147b-947.journal.jsonl5715f040444576404ec7f07e719ac810a9c7424cd0026cdf46d7d78f3ec10b42,107bytes.

Core preflight core_g1seg01_2088_a: exit0, empty stderr, stdout
e852224924b26614cf9cb5ee9565a0d7bbdda28d334221a26e761747bb6b58d2,
identical to Codex's final preflight. The6 original run files are unchanged;
there is no finalization, second Workflow or attempt2.

## Ruling

The running Claude Code2.1.261 implementation identifies this as its auto-mode
workflow permission classifier: the dispatch gate checks auto mode, then v3n
classifies the proposed subagent action in the parent permission context.
This is NOT a Sonnet answer or evidence that Sonnet rejected the task. The
available reason is only "Blocked by classifier"; its underlying reason is
unknown. Do not invent a provider/content defect or change settings to evade it.

Stopping was correct. Core's added claim that ingestion would permanently
mark52 empty answers is unsupported by the live owner: capture_results
requires text or error, and finalization requires the native audit before
writing a final result. Missing worker/raw evidence cannot become52 accepted
empty answers. No synthetic reply, new finalizer or grader patch is warranted.

The normal owner-controlled permission/approval path must resolve the blocked
action. No prompt/model/route change, fresh Workflow, resume or retry is
authorized here. After resolution Codex must approve the exact lawful
continuation under existing resume rules, retaining the refusal. Nothing
requires redoing the key or382 answers. First blocked audit in this goal turn;
keep the existing watcher/goal, not a duplicate or premature completed goal.
