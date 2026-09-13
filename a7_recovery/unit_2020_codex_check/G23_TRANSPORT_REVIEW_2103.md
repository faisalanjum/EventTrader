# Supported G2/G3 execution location — independent check

Codex, 2026-09-13. This supersedes only2100's unrun execution locations.
No A7 score or new model call. The approved partial-report policy and all
grading code, questions, evidence, runtime settings and call counts are unchanged.

## Reproduced problem and smallest correction

The platform refused the zero-agent script at a recovery path. Codex read the
actual Core transcript request and response, not just the report:
`toolu_01XxgmoxmG7CwJWpKMiU7pWx`, request UUID
`e9e6deb2-a66b-481b-abdd-db5d7af6a71e` at08:01:19.095Z; result UUID
`f292d1a0-e278-49fb-8065-5d750e81a1a5` at08:01:19.134Z.
The tool error explicitly requires a previously returned or already-readable
script path. No worker/model ran. Probe outcome:
`../unit_2102_transport_probe/PROBE_OUTCOME_2102.json`,
SHA256 `4146005170711874275c35930226ef6df6b3fca7d3532eecf065ebc8dbcac100`.
This is a path/permission check, not a model safety refusal or a syntax test.

Use the SAME supported-path arrangement already used for194 completed G1
calls in2088. The original publisher pins the actual logical execution path
BEFORE any call. The existing runner maps that path to a durable recovery
directory for verification and ingestion. No symlink/hardlink, permission
change, relaxed samefile check, new transport or copied old receipt.

`freeze_g23_transport_2103.py`, SHA256
`3b5d6250cb2c42b1e2cc91bc330fc0f5900a82a3fdc7a6ea1ec1bc895fe45fda`,
is bounded preparation, not a runtime owner. The new map
`map_g23_transport_2103.tsv`, SHA256
`54e8501050dae0b7e6cd211bbe2164c5e205cd308c2409412b08b8431e8fefa5`,
preserves all167 existing rows and adds only two existing-boundary RW rows.

## Exact new identities

Durable roots: `../unit_2103_g23_grading/{G2,G3}/run`.
Execution roots:
`/tmp/claude-1000/-home-faisal-EventMarketDB/5ae9b86b-f0f6-4449-beee-9cac7cfa7200/scratchpad/a7_grading_2103/{G2,G3}/run`.
Core must materialize each already-published script there without changing
bytes or overwriting a different existing file. Recovery remains durable.

| Item | G2 | G3 |
|---|---|---|
| LAUNCH.json | `d736ad8392962291177b64a4a92686d44e0f0a295dafeb3119ec87d417b72d90` | `ac0327f9fde6c450bd6411363e6e28e87e1196c332f8f59e3df3c994482481e4` |
| Root (unchanged) | `1ee010cf06a9a726c5e12c4893031dbdad075f4f39a09c0f92298bbafa8a6a18` | `56eeda65fd0863823531410aeb05b2a54486eda9c44663222e6af86941e44c6e` |
| First receipt | `6973a8a82bbefbb780ef32a4157fafbb9ac0ed0b9775d0943b9b8c08486ef62f` | `4d7d12af09368ae7b996bdbdb1e1a2445c1e2fea1776cc6e9b0197060d9b81a2` |
| First script | `6fd6be0f64c73d4e9762998600e40166507142502d65ea1af8c9aff6e4fab5f5` | `1926c885dfee7cedfdff7aa298ed18d85814405b6f4504e0f699e43eff02d96a` |
| First invocation | `3ad2c0af5a1f360f67626da1cd2bc8f51be3d6b49319939cba5a093d68bd6123` | `8e7dbc549fa4a82beb96476841887d8cf00f1d4a7bce73f0da577ee8748dd8c0` |
| First bytes/lanes |432989/1 |449768/3 |

Both first segments are ALREADY published. Do not prepare either again.
Old2100 roots and evidence remain untouched, but are not authorized for calls.

## Verification and limits

`codex_g23transport2103_a` passed with payload exit0 and empty stderr:
both new roots equal their old roots; all ordered invocation arguments are
identical; script bytes differ ONLY by the fixed-length invocation hash.
Therefore every question, prompt, input, model/effort, owner and count is
unchanged. Both logical files are the exact durable files inside the boundary.
The unchanged operator separately passed `codex_g2preflight2103_a` and
`codex_g3preflight2103_a`. Both corresponding `wrongreceipt2103_a` controls
refused the deliberately wrong external receipt hash. No actual file was tampered.
Raw stdout/stderr/exit files are in `../unit_1947/logs/attempt_<tag>/`.
The698-pass affected regression and focused/mutation proof remain applicable:
this correction changes no grading owner or answer bytes.

Core2103 reported an additional explicit-user-request rule for Workflow;
Codex2103 requires the exact tool wording and a readiness ruling, not a new
call or permission bypass. That platform gate must hold before actual launch.
Publication may preserve verified preparation while the call gate is pending;
it is not a claim that a model call has succeeded.

172 primaries remain:140 G2 and32 G3.862 prior actual calls,1034 after
primaries,1206 maximum with the existing single invalid-only retry per row.
Never repeat a successful call. All382 producer replies and194 G1 results
remain unchanged. No DB/production/main action or A8 permission.
