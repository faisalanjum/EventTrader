# Judge Integration Contract — **LOCKED 2026-05-29**

The binding rules for every **real LLM judge** in the driver harness. The pure
engine (`synonym_fold.py`) NEVER calls an LLM — it takes an injected
`judge_fn`. The real judge lives in `judge_llm.py` (outside the engine) and is
built to THIS contract. Future passes/tests MUST exercise the real call path
(opt-in), not only deterministic stubs.

---

## 1. The seam (mirror Harness_BuilderPrompt.md §13)

```
judge_fn(packet) -> verdict
```
Injectable callable. The engine knows nothing about LLMs; it only depends on
this shape.

## 2. Packet (engine -> judge) — produced by the engine, N=2-cleared only

```json
{
  "kind": "synonym",
  "from_token": "<str>",
  "candidates": [
    { "to_token": "<str>", "observation_count": <int >= 2>, "sample_evidence": ["<str>", ...] }
  ]
}
```
The eligibility gate is CODE, run BEFORE the judge — the judge NEVER sees a
sub-N=2 candidate.

## 3. Verdict (judge -> engine) — STRICT Structured Outputs

`text={"format":{"type":"json_schema","name":"synonym_judge_verdict","strict":true,"schema":...}}`
(canonical schema lives in the prompt file's `JUDGE:SCHEMA` block).

```json
{ "decision": "promote" | "no_global_rule" | "defer", "to_token": "<str>|null", "reason": "<str>" }
```
**Verified (2026-05-29):** OpenAI Structured Outputs with `strict:true` enforce
schema adherence (shape/types/enum/required), unlike JSON mode which only
guarantees valid JSON. Strict mode requires: all properties in `required`,
optional via `"null"` union, `additionalProperties:false`.

## 4. Post-validation (CODE — the schema cannot express these)

Applied in `judge_llm.py` to every model verdict, in order:
1. `decision` ∉ {promote, no_global_rule, defer} -> **defer**.
2. `decision == "promote"` and (`to_token` null OR `to_token` ∉ packet candidates) -> **defer** (never guess a token).
3. `decision != "promote"` and `to_token` non-null -> coerce `to_token = null`.
4. one promoted `to_token` per `(kind, from_token)` stays the engine's invariant.

## 5. Model policy (tiered)

| role | model | when |
|---|---|---|
| **default** | `gpt-5.4-mini` | every judge call |
| **escalate (unsure)** | `gpt-5.4` | default returns `defer` ("hard case") — ask the stronger model once; its verdict is final (if it also defers, verdict = `defer`) |
| **confirm (risky)** | `gpt-5.4` | default returns `promote` — `promote` is the irreversible-ish action, so CONFIRM: keep `promote` ONLY if `gpt-5.4` agrees on the SAME `to_token`; if it says `no_global_rule`, use that; otherwise `defer`. (verify merges, not just uncertainty) |
| not escalated | — | `no_global_rule` is a definitive, safe "don't fold" — taken as-is |
| alt | `gpt-5-mini` | documented swap **only if** it matches `gpt-5.4-mini` quality (cost option) |
| excluded | `gpt-5.5`, `gpt-4o*` | too new/expensive · retiring |

`temperature=0.0`. `model_policy` id (for the cache key) = `"gpt-5.4-mini>[defer,promote]>gpt-5.4"`.
Escalation triggers (default `defer` -> decide; default `promote` -> confirm) are
project decisions, changed here.

## 6. Failure policy — **defer, never guess**

ANY of: model/network unavailable, refusal, non-JSON, schema violation,
post-validation failure (§4), missing key, or a failed promote-confirmation ->
return `{"decision":"defer","to_token":null,"reason":"<failure cause>"}`. A judge
outage never hard-blocks a run and never fabricates a global fold (mirrors
CombinedPlan §E27 "judge-unavailable degradation").

**Failure-path defers are NOT cached** (§7): returned for the CURRENT run only,
re-judged next run. Only a GENUINE semantic verdict (`promote`, `no_global_rule`,
or a model-reasoned `defer`) is persisted — so a transient outage can never
become a permanent verdict.

## 7. Cache — decide once, replay by code

```
cache_key = sha256( canonical_json(packet) + prompt_version + prompt_content_hash + model_policy )
```
`canonical_json` = `json.dumps(packet, sort_keys=True, separators=(",",":"))`;
fields joined by `\x1f`. **`prompt_content_hash`** = sha256 of the exact
(system + schema) sent to the model, so editing `synonym_judge.v1.md` WITHOUT a
version bump auto-invalidates cached verdicts (no silent stale replay). Same
packet + version + content + model policy -> the **final** (post-escalation)
verdict is replayed, no second API call.

**Backend.** A simple append-only **JSONL `FileCache`** under
`drivers_harness/.judge_cache/` is the default for real runs (decide-once ACROSS
runs); unit tests inject an in-memory `dict` (no disk I/O). A shared/persistent
production backend (Neo4j / SQLite-at-scale) is **integration-phase** — only the
KEY formula above is locked here.

**Cacheability (§6).** Only genuine SEMANTIC verdicts are written. A failure-path
defer (outage / refusal / invalid JSON / schema or post-validation failure /
missing key / failed promote-confirmation) is returned for this run but NOT
persisted — it retries next run.

## 8. Purity & wiring

- `synonym_fold.py` is PURE (no I/O / network / LLM). UNCHANGED by this work.
- `judge_llm.py` (network, key, cache) sits OUTSIDE and builds a `judge_fn`
  injected via `SynonymFoldEngine(judge_fn=make_synonym_judge_fn(...))`.
- The OpenAI client is created lazily (only on a real call), so importing
  `judge_llm` for unit tests needs no key/network.

## 9. Test policy (Hybrid — both, always)

- **Deterministic unit tests** (`tests/test_judge_llm.py`, default suite, NO
  network): a fake transport drives every contract path — defer-on-failure,
  post-validation rules, escalation, cache key + hit. Keeps the suite fast,
  free, deterministic, **0 skipped**.
- **Live tests** (`tests/test_synonym_judge_live.py`, `@pytest.mark.llm`,
  **opt-in**): real OpenAI calls via the real transport. Excluded from the
  default run by `addopts = -m "not llm"`; run with `pytest -m llm`.
- Future passes MUST keep BOTH. "Green" on the deterministic suite is necessary
  but NOT sufficient proof of the real path — the live tests are the proof.

## 10. Prompt registry

| judge | prompt file | status |
|---|---|---|
| synonym | `synonym_judge.v1.md` | **LIVE** — wired into `SynonymFoldEngine` |
| new-name / shortcut admission | `new_name_judge.v1.md` | **SPEC** — call-site (driver_write_cli §E27/§383) not built; integration phase |
| merge / reconciliation | `merge_judge.v1.md` | **SPEC** — call-site (reconciliation job §E27/§395) not built; integration phase |
