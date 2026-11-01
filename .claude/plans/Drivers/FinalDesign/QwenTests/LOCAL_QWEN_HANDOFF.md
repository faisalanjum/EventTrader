# Local Qwen connection handoff

> **Status:** Reference supplied by the owner on 2026-07-24. This records how
> Qwen-specific test runners should call the shared local client. It does not
> authorize a model run. Re-run the preflight and freeze the live model,
> settings, prompts, inputs, answer-key hashes, and scorers before each test.

## Connection code

Client to import:

```text
/home/faisal/EventMarketDB/config/local_llm.py
```

Call pattern:

```python
import sys

sys.path.insert(0, "/home/faisal/EventMarketDB")
from config import local_llm as L

# Free text -> str, or (str, stats) with with_stats=True.
text = L.generate(prompt, system=None, max_tokens=4096)

# Structured output -> dict, or (dict, stats) with with_stats=True.
# The default GGUF path uses JSON-schema grammar enforcement.
obj = L.structured(prompt, schema_dict, system=None)

L.health()          # {host, model, version, num_ctx, input_token_budget, loaded}
L.reason(prompt)    # reasoning on (slow)
L.fast()            # reasoning off (default)
```

Catch these exceptions. They mean the request failed structurally and must
never be treated as a valid model answer:

- `L.TruncatedInputError`: the prompt exceeded the input budget and its front
  would be lost.
- `L.TruncatedOutputError`: output reached the context limit when no
  `max_tokens` value was supplied.

Useful constants:

- `L.MODEL` defaults to `qwen3.6:35b-a3b`.
- `L.NUM_CTX` defaults to `32768`.

## Hard constraints

1. The input budget is about 16,000 tokens: `num_ctx 32768 / 2`, or roughly
   55,000–60,000 characters. Larger input raises `TruncatedInputError`. Tell
   Faisal the largest required case if this budget must be raised.
2. Do not vary `num_ctx` by case. Changing it forces an approximately
   eight-second model reload.
3. Use one model for the whole test run. VRAM holds one model and switching
   costs about 8–14 seconds. The default GGUF model enforces the JSON schema;
   `LOCAL_LLM_MODEL=qwen3.6:35b-mlx` is faster but does not enforce it.
4. Aggregate throughput is about 50 tokens per second regardless of
   concurrency because GPU memory bandwidth is the limit. Four workers may
   fill idle gaps but do not multiply throughput. Estimate wall-clock time as
   total output tokens divided by 50.
5. Temperature zero is the default and has produced byte-identical,
   deterministic output in the supplied checks.

## Shared reference runner

```text
/home/faisal/EventMarketDB/config/run_qwen.py
```

It provides the reusable transport pattern:

```text
cases.jsonl -> results.jsonl
```

It is resumable and supports `--workers`. Its header records the full
input/output contract and all nine transport constraints. The supplied
verification result was: two of three demo cases completed, and the oversized
case failed loudly with `TruncatedInputError`.

The Qwen task runners under this folder may copy its transport pattern or call
it directly. Hidden answers and task-specific scoring must remain outside the
model prompt.

## Sanity check

Run before preparing or executing a Qwen test:

```bash
cd /home/faisal/EventMarketDB
python3 config/preflight.py
```

The supplied expected result is 13 structural checks with process exit code
zero.
