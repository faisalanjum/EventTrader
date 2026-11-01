# How to use DeepSeek V4 Flash via OpenRouter

OpenRouter is OpenAI-API-compatible — same request shape as OpenAI, just a
different base URL, key, and model id. Verified working 2026-07-12.

## Essentials

| | |
|---|---|
| Endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| Auth header | `Authorization: Bearer $OPENROUTER_API_KEY` |
| Model id | `deepseek/deepseek-v4-flash` |
| Billing | Metered OpenRouter credit (pay-per-token) — **NOT** the ChatGPT/Codex subscription |
| Price (default, do-nothing) | ~$0.14 / $0.28 per 1M — OpenRouter's default balancer (it is **not** cheapest-first; no account policy filter is involved) |
| Price (recommended route) | **~$0.077–0.098 / $0.154–0.196 per 1M** — add `"provider": {"sort": "price", "quantizations": ["fp8"]}` (baked into the examples below). Routes to the cheapest **fp8** endpoint (StreamLake $0.077 → falls back to GMICloud/Baidu ~$0.098). Pinning `fp8` avoids a silent **fp4** (lower-quality) downgrade. Verified 2026-07-12. |
| Context window | 1,048,576 tokens (~1M) |

The key lives in env var `OPENROUTER_API_KEY` (repo `.env`, K8s Secret
`eventtrader-secrets` in `processing` + `mcp-services`). In Python code use
`from eventtrader import keys; keys.OPENROUTER_API_KEY`.

## curl

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek/deepseek-v4-flash",
       "provider":{"sort":"price","quantizations":["fp8"]},
       "messages":[{"role":"user","content":"Hello"}],
       "max_tokens":500}'
```

## Python (OpenAI SDK)

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
resp = client.chat.completions.create(
    model="deepseek/deepseek-v4-flash",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=500,
    # cheapest fp8 endpoint (cost routing that can't silently drop to fp4)
    extra_body={"provider": {"sort": "price", "quantizations": ["fp8"]}},
)
print(resp.choices[0].message.content)
```

## Gotchas (learned by testing)

- **Reasoning works** (enabled 2026-07-12). Supports `reasoning_effort`
  (`low` / `medium` / `high` — **no** `xhigh` / `max`; those are Codex-CLI-only.
  For finer control use `reasoning: { max_tokens: N }`). Add `include_reasoning: true`
  to get the trace. It was initially 404-blocked by account privacy; unblocked via
  **openrouter.ai/settings/privacy**: ZDR **"Non-frontier" = OFF**,
  **"Paid endpoints that may train on request data" = ON**, **Allowed Providers = empty**.
  Caveat: with those settings it may route to **China-hosted providers** (seen: Alibaba).
  For sensitive data, pin Western providers via **Allowed Providers** or the request
  `provider: { order: [...], allow_fallbacks: false }` field.
- Response `model` comes back dated (e.g. `deepseek-v4-flash-20260423`) — normal.
- **Not bit-identical across providers.** Same weights / model-id, but each provider
  serves a **quantized** copy: `fp8` (near-full quality), `fp4` (more compressed, can be
  measurably worse), or undisclosed. No endpoint here advertises full `bf16`. The
  `quantizations: ["fp8"]` filter (in the examples) locks precision so price-routing
  can't silently drop you to fp4. Closest to a "reference" copy = DeepSeek's own
  endpoint (`provider: {order: ["deepseek"]}`, ~$0.14, precision undisclosed).
- Set a sane `max_tokens`; don't go tiny (some providers reject `< 16`).
- Check credit/auth without spending tokens: `GET /api/v1/key`.
- Per-provider price breakdown: `GET /api/v1/models/deepseek/deepseek-v4-flash/endpoints`.
