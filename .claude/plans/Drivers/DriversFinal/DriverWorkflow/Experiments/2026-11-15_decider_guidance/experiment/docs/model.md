---
license: apache-2.0
base_model: Qwen/Qwen3.8-27B
base_model_relation: finetune
library_name: pytorch
pipeline_tag: text-classification
tags:
  - classification
  - multimodal
  - custom-code
  - decider
---

# pplx-decider-v1.3

pplx-decider-v1.3 is the next version of [pplx-decider-v1.2](https://huggingface.co/perplexity-ai/pplx-decider-v1.2), a multimodal classification model on Qwen3.8-27B.
It comes with improved performance and robustness across decision tasks, and a new extraction capability: [Locate](#locate-verbatim-span-extraction),
which extracts verbatim text spans from the state with character offsets and confidence scores.

If you are interested in the performance of the models, how we train it and evaluate it, as well as use cases examples, you can read the blogpost here: https://www.perplexity.ai/hub/blog/perplexity-decider

## Usage

Requirements: Python 3.12+ and a CUDA GPU with room for about 49 GiB of BF16 weights plus working memory.
The repository is private: authenticate with a Hugging Face token that has access to it.
Download the repository and install `requirements.txt` (torch, transformers, safetensors, pillow, torchvision, huggingface-hub).

```python
import sys
from pathlib import Path
from huggingface_hub import snapshot_download

checkpoint = Path(snapshot_download("perplexity-ai/pplx-decider-v1.3"))
sys.path.insert(0, str(checkpoint / "source" / "src"))
from pplx_decider import Decider

decider = Decider.from_pretrained(checkpoint, device="cuda")
response = decider.decide({
    "state": "My integration keeps failing with a 401 since we rotated our API key. Please help.",
    "questions": {
        "team": {
            "type": "choice",
            "instructions": "Which team should handle this request?",
            "criteria": {
                "billing": "Charges and refunds",
                "support": "Technical integration errors",
                "sales": "Questions about buying a product",
            },
        },
        "urgent": {"type": "noul", "instructions": "Is the customer blocked right now?"},
        "frustration": {"type": "score", "criteria": ["calm", "mildly annoyed", "frustrated", "angry"]},
    },
})
print(response["answers"]["team"]["choice"], response["answers"]["urgent"]["noul"])
```

`decide` accepts one request and returns one response. Given a list of requests, it returns a list of responses in
the same order. The source can also be installed as a package: `pip install ./source`.

### Request schema

```python
{
  "state": str | dict | list,            # the context to classify; non-strings are serialized as JSON
  "questions": {                         # 1 or more questions, answered from the same state
    "<id>": {
      "type": "choice" | "noul" | "score" | "locate",
      "instructions": str | None,        # optional; for Locate, refines/replaces the question key
      "criteria": ...,                   # see below
    },
  },
  "images": [path | "data:image/...;base64,..." | PIL.Image],   # optional
}
```

| Type | `criteria` | Answer |
|---|---|---|
| `choice` | `{option_name: description or None}`, 1 to 255 options | `choice`, `probabilities` (per option), `confidence` |
| `noul` | optional `{"true": description, "false": description}` | `noul` = P(true) |
| `score` | list of 2 to 255 level descriptions, lowest first | `score` (expected level index), `probabilities`, `legend`, `confidence` |
| `locate` | not used; question key is the label, optionally replaced by `instructions` | `spans`: `start`, `end`, `text`, `score` |

The options are shown to the model in the order you give them, under the answer codes `A`, `B`, ... Each response
looks like `{"answers": {"<id>": {...}}, "usage": {"input_tokens": int, "output_tokens": 0, "sequences": int}}`.
Requests that do not follow the schema raise `pplx_decider.RequestError` before any computation.

`decider.logits(requests)` returns the raw readout logits of each question's valid options, before temperature.
For ranking, use the logit margin `true - false` of a `noul` question: unlike probabilities, it does not saturate
into ties.

## Several questions in one request

For decision questions, a request can carry any number of questions about the same state. By default (`mode="separate"`) each question is answered
in its own sequence, made of the state (and images) and that question only: **questions do not see each other**, and an
answer does not change when you add, remove or reorder the other questions. This is the computation all the scores above
were measured with. Put everything a question needs in the state, not in another question.

`Decider.from_pretrained(..., mode="isolated")` instead encodes a whole request as one sequence with the training-time
layout: the state is read once and each question attends to the state and to itself. It is cheaper when many questions
share a long state, but the state also attends to the questions, so answers can shift slightly with the set of questions
(on our samples, 1.5-2.2% of top answers differ from `separate`). Use `separate` unless the cost of re-reading the state
matters.

## Temperature and calibration

`decision_config.json` stores the temperature fitted on held-out calibration data. `decide` applies it exactly once,
then normalizes a softmax over each question's valid options only. `decide(..., temperature=t)` overrides it. When you
use `logits` directly, divide by the saved temperature before the softmax, and do not include the unused codes.
If your application relies on probability values (rather than rankings or the top answer), calibrate on a sample of
your own traffic: a single temperature cannot be right for every task, and per-task thresholds are usually better.

## Images

Images go in `images`. They are placed before the text of the request, and every question can see them. Each image is
resized (aspect ratio kept) to at most `max_pixels` pixels: **1,638,400 (1.6 MP)**, as saved in
`decision_config.json`. Smaller images keep their size. A 1.6 MP image uses about 1,600 sequence positions, so several
large images count toward the [length limit](#limits). The checkpoint was trained and evaluated at its saved value.

## Fast path

`Decider.from_pretrained(..., fast=True)` (requires `requirements-fast.txt`) packs many sequences per forward pass and
compiles the decoder with `torch.compile`. It supports both modes on all three model sizes:

- `mode="separate"` also replays CUDA graphs. On our validation sample it was about 1.7-1.9x faster than the default
  padded batches, with 99.6-99.7% top-answer agreement with the reference path.
- `mode="isolated"` reads each request's state once and starts every question from it, as the reference isolated path
  does (no CUDA graphs: their shapes depend on the request). On our validation sample it was 9-18x faster than the
  reference isolated path and faster than the separate fast path, with 99.4-99.8% top-answer agreement with the
  reference isolated path.

Differences are BF16 batching noise (mean |Δp| about 0.002, about 0.006 for the mixture-of-experts model). Call
`decider.warmup()` at startup to compile ahead of time. The default path with one request per call reproduces our
evaluation implementation to within 3e-7.

## Locate: verbatim span extraction

Use `"type": "locate"` to extract matching text spans from the state. The question key is the default label:
`"person": {"type": "locate"}` extracts people. Optional `instructions` refines the request by replacing that label,
for example `"person": {"type": "locate", "instructions": "The person who signed the contract"}`.
Missing, null or blank `instructions` uses the key. Locate questions can be mixed with decision questions.
The adapter is loaded automatically on the first Locate request.

```python
decider = Decider.from_pretrained(checkpoint, device="cuda")
response = decider.decide({
    "state": "My integration keeps failing with a 401 since we rotated our API key. Please help.",
    "questions": {
        "urgent": {"type": "noul", "instructions": "Is the customer blocked right now?"},
        "error": {"type": "locate", "instructions": "Error codes"},
    },
})
print(response["answers"]["urgent"]["noul"])
for span in response["answers"]["error"]["spans"]:
    print(span["start"], span["end"], span["text"], span["score"])
```

Locate requires a nonempty text `state`, no images and at most 128 questions per request.
Each span has character offsets `start` and `end` (exclusive), its `text`, and a `score`;
`state[start:end] == text`. No matches returns an empty `spans` list.

Locate questions run together, separately from decisions, and can influence each other through the shared state.
Requests mixing Locate and decision questions require separate forward passes for each type, adding latency
compared with requests containing only one type. Splitting the same work into two `decide()` calls does not
remove these forward passes.

They use the same `max_length` setting (default 32,768 tokens): questions are split only when needed, preserving
the full state. If a single question plus the state cannot fit, `LengthError` is raised.
`fast=True` and `locate=False` disable Locate.

Calls to `decide()`, `logits()`, `reference_logits()` and `warmup()` on the same `Decider` instance
are serialized by an internal lock, including adapter loading. Concurrent callers are safe through these methods;
use separate instances for parallel inference.

## Limits

- **Options:** 1 to 255 per question (2 to 255 for `score`). The answer codes are single tokens, and the readout
  head has 255 rows.
- **Length:** training used sequences up to 30,720 tokens. Inputs are never truncated; validate longer inputs on your own task.
- **Questions per request:** no fixed cap; the length limit is the only constraint.

## Checkpoint format and serving

This is the native decision-checkpoint layout: the backbone plus `readout.safetensors`, a BF16 `[255, hidden_size]`
decision head. `joint_config.json` declares the request protocol (`version: 4`, `joint-chunked-readout-v1`, marker
`<|fim_suffix|>`, separator `<|fim_middle|>`).

- Full-attention layers are **noncausal** over the sequence (the state and the question being answered); the
  linear-attention layers keep their causal behaviour. Default causal inference does not reproduce this checkpoint.
- The readout is applied at each `<|fim_suffix|>` marker, one per question, not at the last token. Literal special
  tokens in user content are neutralized before tokenization, so user text cannot create markers.
- This artifact has a separate readout, **not a full-vocabulary `lm_head`**. Readout row `i` corresponds to vocabulary
  row `decision_config.json["token_ids"][i]`.

`release-manifest.json` records file checksums.

## Troubleshooting

- **Probabilities differ slightly between batch compositions**: expected in BF16. Use one request per call for
  bit-stable results.
- **`LengthError`**: one question with the state and images exceeds `max_length`. Shorten the state or lower
  `max_pixels`.
- **Out of memory**: lower `batch_tokens`.
- **Different answers from v1.1 / v1.2-style prompts**: this model expects the v1.3 format built by `pplx_decider`. Do
  not reuse earlier prompt builders.

## Acknowledgment

A large part of the gains are thanks to the [tasksource](https://github.com/sileod/tasksource) data. If you also use
this data, consider citing the corresponding article

```bibtex
@inproceedings{sileo-2024-tasksource,
    title = "tasksource: A Large Collection of {NLP} tasks with a Structured Dataset Preprocessing Framework",
    author = "Sileo, Damien",
    booktitle = "Proceedings of the 2024 Joint International Conference on Computational Linguistics, Language Resources and Evaluation (LREC-COLING 2024)",
    month = may,
    year = "2024",
    address = "Torino, Italia",
    publisher = "ELRA and ICCL",
    url = "https://aclanthology.org/2024.lrec-main.1361",
    pages = "15655--15684",
}
```
