"""Local LLM client — Qwen3.6-35B served from the Mac over the LAN.

Treats the model as a frontier-grade text/JSON API. The wrapper's job is to make
the plumbing bulletproof, independent of any task:

  * NEVER silently truncate input. The GGUF backend gives the prompt only ~half
    of num_ctx and drops the FRONT when exceeded (verified). We detect that and
    RAISE, rather than let rules/schema silently vanish.
  * Surface output truncation (done_reason == "length") instead of returning a
    quietly-cut answer.
  * Enforce structured output: pass a JSON schema; GGUF grammar-enforces it, and
    structured() also fence-strips + parses + retries as a belt-and-suspenders.
  * Fixed num_ctx by default: changing it forces an ~8s model reload (verified).
  * temperature=0, deterministic (verified byte-identical).
  * Addressed by mDNS name (survives Deloitte DHCP IP changes); IP is fallback.

Model choice (one at a time; VRAM holds one):
  * qwen3.8:27b-mlx  (MLX, default) — 27.8B dense, nvfp4, ~27 t/s. Format is NOT
                                      grammar-enforced (MLX), but measured 19/19
                                      schema-valid on the QF-01 aligned set
                                      (2026-08-15); never truncates input.
    Migrated 2026-08-15 from qwen3.6:35b-a3b (36B MoE/3B-active, GGUF Q4_K_M,
    ~77 t/s, grammar-enforced). The old model scored 17/19 on QF-01-aligned
    (NOT_SAFE_FOR_TASK); qwen3.8 scores 19/19. Trade: ~4x slower decode, dense
    vs MoE. Both qwen3.6 tags were removed 2026-08-15.
"""
from __future__ import annotations

import json
import os
import time
import http.client
import socket
import urllib.request

MODEL = os.getenv("LOCAL_LLM_MODEL", "qwen3.8:27b-mlx")   # MLX default (see notes above)
NUM_CTX = int(os.getenv("LOCAL_LLM_NUM_CTX", "32768"))    # fixed -> no reload thrash
THINK_DEFAULT = os.getenv("LOCAL_LLM_THINK", "0").lower() in ("1", "true", "yes")
TIMEOUT_DEFAULT = int(os.getenv("LOCAL_LLM_TIMEOUT", "1800"))  # s; cold prefill of a
    # 10k-token document on qwen3.8:27b-mlx is ~2 min at ~85 tok/s, and the
    # M4 Pro throttles under sustained load, so 300 s (old default) aborted real calls

HOSTS = [h for h in (
    os.getenv("LOCAL_LLM_HOST"),
    "http://CA-K429CXLGF9.local:11434",
    "http://192.168.40.147:11434",
) if h]

_cached_host: str | None = None


class TruncatedInputError(RuntimeError):
    """The prompt was (or would be) silently cut by the backend. Never ignore."""


class TruncatedOutputError(RuntimeError):
    """Generation stopped at the token/context limit, not a natural stop."""


def _is_mlx(model: str) -> bool:
    return "mlx" in model.lower()


def _input_budget(num_ctx: int, model: str) -> int:
    """Max prompt tokens before the backend truncates.

    GGUF/llama.cpp reserves ~half of num_ctx for generation (verified: a 7k-token
    prompt at num_ctx=8192 was cut to ~4098). MLX reads the full input.
    """
    if _is_mlx(model):
        # MLX reads the full prompt (no half-ctx reserve), but it is still
        # bounded by num_ctx. The old hard-coded 200_000 disabled the guard
        # entirely and allowed silent overflow once num_ctx was right-sized.
        return max(num_ctx // 2, num_ctx - 2048)
    return num_ctx // 2


class _KeepAliveConnection(http.client.HTTPConnection):
    """HTTP connection with TCP keepalive.

    During prompt evaluation the model emits NO tokens, so the socket sits
    idle for minutes on a long prefill. Something on the LAN path reaps
    connections idle for ~300s, which surfaced as
    "[Errno 104] Connection reset by peer" while the SERVER had in fact
    returned 200 (verified in ollama-agent.log: 5m10s / 6m48s / 6m50s all
    HTTP 200). Keepalive probes keep the path warm. Verified 2026-08-16.
    NOTE: TCP_KEEPCNT must be <= 127; larger raises EINVAL.
    """

    def connect(self):
        super().connect()
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except OSError:
            return
        for name, value in (("TCP_KEEPIDLE", 30),
                            ("TCP_KEEPINTVL", 30),
                            ("TCP_KEEPCNT", 60)):
            option = getattr(socket, name, None)
            if option is None:
                continue
            try:
                self.sock.setsockopt(socket.IPPROTO_TCP, option, value)
            except OSError:
                pass


class _KeepAliveHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_KeepAliveConnection, req)


_OPENER = urllib.request.build_opener(_KeepAliveHandler)


def _post(url: str, payload: dict, timeout: int) -> dict:
    """POST to Ollama, always STREAMING, reassembled into the non-streaming
    response shape so every caller is unaffected.

    Why: streaming keeps the socket active during long generations instead of
    leaving it idle until the whole reply is ready.

    CORRECTION 2026-08-16: an earlier version of this note claimed streaming
    turned a 399s call into 1.0s. That was WRONG - it compared a cold prompt
    against one Ollama had already cached. Measured properly, cold prompt
    evaluation on qwen3.8:27b-mlx costs ~340-420s for a 7.5k-token prompt
    either way, and the connection still resets during it because no tokens
    flow while the prompt is being processed. Streaming is retained as a mild
    improvement, not a fix; the real cost is cold prompt eval on a dense
    27B model."""
    payload = dict(payload)
    payload["stream"] = True
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    parts, final = [], {}
    with _OPENER.open(req, timeout=timeout) as r:
        for raw_line in r:
            line = raw_line.strip()
            if not line:
                continue
            chunk = json.loads(line.decode("utf-8"))
            piece = (chunk.get("message") or {}).get("content") or ""
            if piece:
                parts.append(piece)
            if chunk.get("done"):
                final = chunk
    out = dict(final)
    message = dict(out.get("message") or {})
    message["content"] = "".join(parts)
    out["message"] = message
    return out


def resolve_host(force: bool = False) -> str:
    """First reachable Ollama host; cached. Survives IP changes via mDNS."""
    global _cached_host
    if _cached_host and not force:
        return _cached_host
    last = None
    for h in HOSTS:
        try:
            with urllib.request.urlopen(f"{h}/api/version", timeout=5) as r:
                if r.status == 200:
                    _cached_host = h
                    return h
        except Exception as e:  # noqa: BLE001
            last = e
    raise ConnectionError(f"No reachable Ollama host in {HOSTS}: {last}")


def health() -> dict:
    host = resolve_host(force=True)
    out = {"host": host, "model": MODEL, "num_ctx": NUM_CTX,
           "input_token_budget": _input_budget(NUM_CTX, MODEL)}
    try:
        with urllib.request.urlopen(f"{host}/api/version", timeout=5) as r:
            out["version"] = json.loads(r.read().decode()).get("version")
        with urllib.request.urlopen(f"{host}/api/ps", timeout=5) as r:
            out["loaded"] = [m.get("name") for m in
                             json.loads(r.read().decode()).get("models", [])]
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    return out


def generate(
    prompt: str,
    system: str | None = None,
    *,
    format: str | dict | None = None,   # noqa: A002  "json" or a JSON-schema dict
    think: bool | None = None,
    temperature: float = 0.0,
    num_ctx: int = NUM_CTX,
    max_tokens: int | None = None,
    timeout: int | None = None,
    retries: int = 2,
    allow_truncation: bool = False,
    with_stats: bool = False,
):
    """One chat completion. Raises on silent input truncation by default."""
    if think is None:
        think = THINK_DEFAULT
    if timeout is None:
        timeout = TIMEOUT_DEFAULT
    msgs = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}]
    opts = {"temperature": temperature, "num_ctx": num_ctx}
    if max_tokens:
        opts["num_predict"] = max_tokens
    payload = {"model": MODEL, "messages": msgs, "stream": False,
               "think": think, "options": opts}
    if format is not None:
        payload["format"] = format

    last = None
    for attempt in range(retries + 1):
        try:
            host = resolve_host(force=(attempt > 0))
            d = _post(f"{host}/api/chat", payload, timeout)
            break
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"local LLM call failed after {retries + 1} tries: {last}")

    text = (d.get("message", {}) or {}).get("content", "") or ""
    pec = d.get("prompt_eval_count", 0)
    done = d.get("done_reason")
    budget = _input_budget(num_ctx, MODEL)

    # --- silent INPUT truncation: GGUF caps the prompt near num_ctx//2 ---
    trunc_in = (not _is_mlx(MODEL)) and pec >= budget - 8
    if trunc_in and not allow_truncation:
        raise TruncatedInputError(
            f"prompt truncated: {pec} tokens processed at the ~{budget}-token "
            f"input budget (num_ctx={num_ctx}). The FRONT of your prompt was "
            f"dropped. Raise num_ctx to >= 2x your input, shorten the input, or "
            f"pass allow_truncation=True.")

    # --- OUTPUT truncation: stopped at a limit, not a natural stop ---
    trunc_out = (done == "length")
    if trunc_out and max_tokens is None and not allow_truncation:
        raise TruncatedOutputError(
            "generation hit the context limit (done_reason='length') with no "
            "max_tokens set. Raise num_ctx or investigate; output is incomplete.")

    if not with_stats:
        return text
    ed = d.get("eval_duration", 1) / 1e9
    return text, {
        "tok_s": round(d.get("eval_count", 0) / ed, 1) if ed else 0,
        "eval_count": d.get("eval_count", 0),
        "prompt_eval_count": pec,
        "done_reason": done,
        "truncated_input": trunc_in,
        "truncated_output": trunc_out,
        "total_s": round(d.get("total_duration", 0) / 1e9, 2),
        "host": host,
    }


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        t = parts[1] if len(parts) > 1 else t
        t = t.removeprefix("json").strip()
    return t


def _render_prefix(user_prefix: str, system: str | None) -> str:
    """Byte-exact HEAD of what Ollama's built-in Qwen3.5/3.8 renderer emits
    for messages=[system?, user] with think=False (verified against
    ollama/model/renderers/qwen35.go, 2026-08-16):
        <|im_start|>system\n{system.strip()}<|im_end|>\n<|im_start|>user\n{user}
    Only the part up to (inside) the user content is reproduced, so the result
    must be sent with raw=True and is meaningful only as a PREFIX of a later
    ordinary chat call that uses the same system text."""
    head = ""
    if system and system.strip():
        head = "<|im_start|>system" + chr(10) + system.strip() + "<|im_end|>" + chr(10)
    return head + "<|im_start|>user" + chr(10) + user_prefix.lstrip()


def prime(user_prefix: str, system: str | None = None, *,
          num_ctx: int = NUM_CTX, timeout: int | None = None,
          with_stats: bool = False):
    """Warm the server's prefix cache for a prompt prefix that later calls share.

    Why (Ollama x/mlxrunner, verified 2026-08-16): the MLX runner's prefix
    cache only creates a branch-point snapshot during the SECOND request that
    diverges at that point, and qwen3.8's recurrent layers cannot be rewound,
    so every shared document costs TWO cold prefills before cache hits start.
    A raw request whose tokens are exactly the shared prefix leaves an
    automatic snapshot 4 tokens before its end (pipeline.go: preThinking=4),
    so the FIRST real call already restores there.
    Measured: 3 calls on one 6.2k-token table 155 s -> 78 s; answers identical.

    Use when >= 2 upcoming calls will share `user_prefix` byte-for-byte at the
    START of their prompt, with the same `system`, `num_ctx` and model.
    Cost: one prefill of the prefix (a hit if already cached). Output ignored.
    """
    if timeout is None:
        timeout = TIMEOUT_DEFAULT
    payload = {"model": MODEL, "raw": True, "stream": False,
               "prompt": _render_prefix(user_prefix, system),
               "options": {"temperature": 0.0, "num_ctx": num_ctx,
                           "num_predict": 1}}
    host = resolve_host()
    d = _post(f"{host}/api/generate", payload, timeout)
    stats = {"prompt_eval_count": d.get("prompt_eval_count"),
             "prompt_eval_s": round((d.get("prompt_eval_duration") or 0) / 1e9, 3),
             "total_s": round((d.get("total_duration") or 0) / 1e9, 3),
             "host": host, "model": MODEL, "num_ctx": num_ctx}
    return stats if with_stats else None


def shared_prefix(prompts, *, min_chars: int = 200) -> str | None:
    """Longest common prefix of the prompts, cut back to a line boundary; None
    when there is nothing worth priming (< 2 prompts or a short prefix)."""
    prompts = [p for p in prompts if isinstance(p, str)]
    if len(prompts) < 2:
        return None
    common = os.path.commonprefix(prompts)
    cut = common.rfind(chr(10)) + 1
    common = common[:cut]
    return common if len(common) >= min_chars else None


def prime_for(prompts, system: str | None = None, **kw):
    """prime() the shared prefix of a batch of prompts over one document.
    Returns the prime stats, or None when nothing was primed."""
    prefix = shared_prefix(prompts)
    if prefix is None:
        return None
    return prime(prefix, system, with_stats=True, **kw)


def structured(prompt: str, schema: str | dict, system: str | None = None,
               *, retries: int = 2, with_stats: bool = False, **kw):
    """Return a parsed JSON object matching `schema` (or (obj, stats)).

    Pass a JSON-schema dict (GGUF grammar-enforces it) or the string "json".
    Fence-strips + parses + retries, so it is robust even on the MLX model.
    """
    kw["format"] = schema
    if _is_mlx(MODEL) and isinstance(prompt, str):
        # MLX does NOT grammar-enforce the "format" schema; without an
        # explicit instruction the model answers in prose. Verified
        # 2026-08-15 (bare prompt -> prose; +instruction -> valid JSON).
        prompt = prompt + chr(10) + chr(10) + (
            "Return JSON only - exactly one object matching the schema, "
            "no prose, no code fence.")
    last = None
    txt = ""
    for _ in range(retries + 1):
        txt, stats = generate(prompt, system, with_stats=True, **kw)
        try:
            obj = json.loads(_strip_fences(txt))
            return (obj, stats) if with_stats else obj
        except Exception as e:  # noqa: BLE001
            last = e
    raise ValueError(
        f"no valid JSON after {retries + 1} tries ({last}); last={txt[:200]!r}")


def fast(prompt: str, system: str | None = None, **kw):
    """Reasoning explicitly OFF (production default path)."""
    kw["think"] = False
    return generate(prompt, system, **kw)


def reason(prompt: str, system: str | None = None, **kw):
    """Reasoning ON. Much slower; only for genuinely hard multi-step analysis."""
    kw["think"] = True
    kw.setdefault("timeout", 900)
    return generate(prompt, system, **kw)


if __name__ == "__main__":
    import sys
    print("health:", json.dumps(health(), indent=2))
    q = sys.argv[1] if len(sys.argv) > 1 else "Reply with exactly: OK"
    txt, st = generate(q, with_stats=True)
    print("\nresponse:", txt.strip()[:400])
    print("stats:", json.dumps(st, indent=2))
