#!/usr/bin/env python3
"""Patch config/local_llm.py: add prefix priming + env-configurable timeout.
Idempotent. Usage: python3 patch_local_llm_prime.py <path/to/local_llm.py>
"""
import sys, shutil, time, re

path = sys.argv[1]
src = open(path, encoding="utf-8").read()
if "def prime(" in src:
    print("already patched:", path)
    sys.exit(0)

bak = f"{path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(path, bak)
print("backup:", bak)

# 1) env-configurable default timeout (was a hardcoded 300 in generate())
old_defaults = 'THINK_DEFAULT = os.getenv("LOCAL_LLM_THINK", "0").lower() in ("1", "true", "yes")\n'
assert old_defaults in src, "THINK_DEFAULT line not found"
new_defaults = old_defaults + (
    'TIMEOUT_DEFAULT = int(os.getenv("LOCAL_LLM_TIMEOUT", "1800"))  # s; cold prefill of a\n'
    '    # 10k-token document on qwen3.8:27b-mlx is ~2 min at ~85 tok/s, and the\n'
    '    # M4 Pro throttles under sustained load, so 300 s (old default) aborted real calls\n'
)
src = src.replace(old_defaults, new_defaults, 1)

old_sig = "    timeout: int = 300,\n    retries: int = 2,\n    allow_truncation: bool = False,\n    with_stats: bool = False,\n):\n    \"\"\"One chat completion."
assert old_sig in src, "generate() signature not found"
src = src.replace(old_sig, old_sig.replace("timeout: int = 300,", "timeout: int | None = None,"), 1)
old_body = '    if think is None:\n        think = THINK_DEFAULT\n    msgs = ('
assert old_body in src
src = src.replace(old_body, '    if think is None:\n        think = THINK_DEFAULT\n    if timeout is None:\n        timeout = TIMEOUT_DEFAULT\n    msgs = (', 1)

# 2) prime() / prime_for() inserted before structured()
anchor = "def structured(prompt: str, schema: str | dict, system: str | None = None,"
assert anchor in src
prime_code = '''def _render_prefix(user_prefix: str, system: str | None) -> str:
    """Byte-exact HEAD of what Ollama's built-in Qwen3.5/3.8 renderer emits
    for messages=[system?, user] with think=False (verified against
    ollama/model/renderers/qwen35.go, 2026-08-16):
        <|im_start|>system\\n{system.strip()}<|im_end|>\\n<|im_start|>user\\n{user}
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


'''
src = src.replace(anchor, prime_code + anchor, 1)
open(path, "w", encoding="utf-8").write(src)
import py_compile
py_compile.compile(path, doraise=True)
print("patched + compiled OK:", path)
