# Perplexity Decider v1.3 on the Mac: how to call it

Classifier and span finder, not a text generator. It answers questions about one text ("state"):
`choice` (pick an option), `noul` (yes/no probability), `score` (ordered levels), and `locate` (exact passages copied
from the text, with character positions). Text only for now: the image part of the model is installed but this
runtime does not read images yet.

## Where

`POST http://localhost:11435/api/decide` — same adapter and port as the local Qwen models. On the Mac it is
127.0.0.1:11435; on the Minisforum the SSH tunnel serves it at localhost:11435 (Python: `config/local_llm.py`
`decide()`). Model name: `pplx-decider-v1.3:8bit` (listed by `GET /api/tags`).

## Request

```json
{
  "model": "pplx-decider-v1.3:8bit",
  "state": "text to judge (or any JSON value, which is serialized)",
  "questions": {
    "team":    {"type": "choice", "instructions": "Which team should handle this?",
                "criteria": {"billing": "Charges and refunds", "support": "Technical errors", "sales": null}},
    "urgent":  {"type": "noul", "instructions": "Is the customer blocked right now?"},
    "anger":   {"type": "score", "criteria": ["calm", "annoyed", "frustrated", "angry"]},
    "codes":   {"type": "locate", "instructions": "Error codes"}
  },
  "mode": "isolated"
}
```

- `choice`: `criteria` maps 1-255 option names to a description or null. `noul`: optional
  `criteria` `{"true": "...", "false": "..."}`. `score`: `criteria` is a list of 2-255 levels, lowest first.
  `locate`: no criteria; the label is `instructions`, or the question key if `instructions` is missing. Locate needs a
  text state; at most 128 Locate questions per request.
- `instructions` is optional for decisions (default "Choose the best matching option.").
- `mode` (optional): `"isolated"` (default) or `"separate"` — see below.
- `temperature` (optional): overrides the saved calibration temperature (1.2264). Leave it out normally.

## Response

```json
{"model": "pplx-decider-v1.3:8bit",
 "answers": {
   "team":   {"type": "choice", "choice": "support", "probabilities": {"billing": 0.0, "support": 0.9995, "sales": 0.0004}, "confidence": 0.999},
   "urgent": {"type": "noul", "noul": 0.65},
   "anger":  {"type": "score", "score": 1.2, "probabilities": {"0": 0.1, "1": 0.6, "2": 0.25, "3": 0.05}, "legend": {"0": "calm", "1": "annoyed", "2": "frustrated", "3": "angry"}, "confidence": 0.7},
   "codes":  {"type": "locate", "spans": [{"start": 36, "end": 39, "text": "401", "score": 0.9998}]}},
 "usage": {"input_tokens": 230, "output_tokens": 0, "sequences": 2}}
```

`noul` is P(true). Locate spans satisfy `state[start:end] == text` (end exclusive) and are kept at score >= 0.5.
Probabilities are calibrated on Perplexity's data; for decisions that matter, pick thresholds on a sample of your own.

## Modes

| | isolated (default) | separate |
|---|---|---|
| How | The text is read once for all decision questions, and once for all Locate questions | One full pass per question |
| Speed | About 3x faster with several questions (8k tokens: 3 questions 90 s, 4 Locate labels 84 s) | Time x number of questions |
| Answers | Can shift slightly with the set of questions (Perplexity: 1.5-2.2% of top answers; our test: 1 of 23, mean probability change 3%) | Independent of the other questions; the computation behind Perplexity's published scores |

With one question of a type, both modes give the same result. Use `separate` when answers must not depend on which
other questions are asked; use `isolated` for bulk work with several questions per text.

## Limits and speed

- At most 32,768 tokens per sequence (the text plus the question; in isolated mode the text plus all questions of a
  type). Longer requests are refused with HTTP 400 and nothing is cut. Peak GPU memory at the limit: 34.7 GiB.
- Speed: about 85 tokens of input per second per pass (2k tokens ~22 s, 8k ~85 s, 16k ~175 s, 32k ~6.5 min),
  measured in High Power Mode; slower when the Mac is hot. A short text answers in 1-3 s.
- One model in memory at a time: a Decider call unloads Qwen and a Qwen call unloads the Decider. The first call after a
  switch also loads the model (about 15-30 s). Group calls by model. The engine unloads after 15 idle minutes.
- One request runs at a time; others wait.

## Errors

400: bad request (message says what) or too long. 404: unknown model or path. 503: the engine could not start
(see `~/Developer/local-llm/decider/server.log`). 502: the worker failed during the request.

## Accuracy notes (tests in `tests/`)

- 8-bit vs full precision: same top answer on 23 of 23 questions, mean probability difference 0.4%, all Locate
  passages identical. Model inputs are token-for-token identical to Perplexity's `pplx_decider` code.
- Locate finds named things well (people, organisations, places, emails, codes). On an 8k-token filing, abstract labels
  such as "the company's own forecasts" returned almost nothing; test labels on your own texts first.
- Punctuation fix (15 Nov): the tokenizer joins punctuation to a value symbol ("%.", "%,", "%)", " ($", '"$') or an
  opening mark to a word ('"We'), and Locate can only cut spans between tokens, so it missed e.g. "18.5%." (Perplexity's
  own code tokenizes the same way). This runtime now cuts those tokens apart for Locate only. Text and character positions
  are unchanged; decisions are bit-identical (23/23). Test `tests/locate_boundaries.py` (52 cases, 60 expected
  spans): 45 → 56 found, extra spans 3 → 1, missing-fact cases still empty, the 10 eval Locate questions unchanged
  (= 16-bit reference), the 1,028-word report 3/4 → 4/4. Dates, names, companies and places unchanged. Still missed
  (model, not punctuation): "Contoso" in quotes, "Toronto" in curly quotes, two names after "Dr."/"Ms.". Offline check
  `tests/locate_encoding_check.py`: only joined tokens change (15 of 44,327 on the test texts), and the pieces cover
  the text exactly. Previous runtime: `decider_mlx.py.bak-2026-11-15`.
