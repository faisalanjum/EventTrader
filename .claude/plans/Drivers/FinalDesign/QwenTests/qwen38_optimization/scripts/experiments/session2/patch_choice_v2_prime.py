#!/usr/bin/env python3
"""Patch the SHADOW choice_v2.py: per-family prefix priming + env NUM_CTX.
Usage: python3 patch_choice_v2_prime.py <path/to/choice_v2.py>"""
import sys, shutil, time, py_compile

path = sys.argv[1]
src = open(path, encoding="utf-8").read()
if "PRIME_PREFIX" in src:
    print("already patched"); sys.exit(0)
bak = f"{path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(path, bak); print("backup:", bak)

assert "\nimport os\n" in src or "import os" in src.split("\n\n")[0] or "import os" in src, "need import os"

old = 'NUM_CTX = 16_384\nMAX_TOKENS = 512\nTIMEOUT_SECONDS = 1800\nWORKERS = 1\n'
assert old in src
new = ('# num_ctx is configurable at PREPARE time (frozen into the manifest, verified at\n'
       '# run time). Keep it fixed for a whole run: changing it reloads the model and\n'
       '# drops the server prefix cache. 16384 comfortably holds the largest dense prompt\n'
       '# (~6.3k tokens) plus output; larger values cost KV memory and prefill time.\n'
       'NUM_CTX = int(os.environ.get("QWEN_NUM_CTX", "16384"))\n'
       'MAX_TOKENS = 512\n'
       'TIMEOUT_SECONDS = 1800\n'
       'WORKERS = 1\n'
       '# Prefix priming (QWEN_PRIME=0 disables): before the first call of each family,\n'
       '# send the family\'s shared prompt prefix once (raw) so the server leaves a cache\n'
       '# snapshot at the branch point. Prompt bytes per case are UNCHANGED; this only\n'
       '# removes the second cold prefill per table. See config/local_llm.py: prime().\n'
       'PRIME_PREFIX = os.environ.get("QWEN_PRIME", "1") != "0"\n')
src = src.replace(old, new, 1)

old_loop = '''    mode = "a" if RAW_RESULTS_PATH.exists() else "x"
    with RAW_RESULTS_PATH.open(mode, encoding="utf-8") as handle:
        for number, case in enumerate(pending, 1):
            result = run_one(case)
'''
assert old_loop in src
new_loop = '''    families = {}
    for case in cases:
        families.setdefault(_family_of(case), []).append(case["prompt"])
    prime_log = []
    last_family = None

    mode = "a" if RAW_RESULTS_PATH.exists() else "x"
    with RAW_RESULTS_PATH.open(mode, encoding="utf-8") as handle:
        for number, case in enumerate(pending, 1):
            family = _family_of(case)
            if PRIME_PREFIX and family != last_family:
                prime_log.append(_prime_family(family, families[family]))
            last_family = family
            result = run_one(case)
'''
src = src.replace(old_loop, new_loop, 1)

old_rec = '''        "model_before": manifest["model"],
        "model_after": model_fingerprint(),
        "scored": False,
    }
    if record["model_after"] != record["model_before"]:
        raise RuntimeError("model changed during run")
    write_json_atomic(RUN_RECORD_PATH, record)
    return record
'''
assert old_rec in src
new_rec = '''        "model_before": manifest["model"],
        "model_after": model_fingerprint(),
        "prefix_priming": PRIME_PREFIX,
        "prime_calls": prime_log,
        "scored": False,
    }
    if record["model_after"] != record["model_before"]:
        raise RuntimeError("model changed during run")
    write_json_atomic(RUN_RECORD_PATH, record)
    return record
'''
src = src.replace(old_rec, new_rec, 1)

helpers = '''

def _family_of(case: dict) -> str:
    """SCR-11-q3 -> SCR-11: all cases of a family share one source table."""
    return case["id"].rsplit("-", 1)[0]


def _prime_family(family: str, prompts: list[str]) -> dict:
    """Prime the server prefix cache with the family's shared prompt prefix.
    Never fails the run: priming is a pure cache warm-up (its output is
    discarded and no case prompt changes)."""
    started = time.monotonic()
    entry = {"family": family, "cases": len(prompts)}
    try:
        stats = L.prime_for(prompts, SYSTEM_MESSAGE, num_ctx=NUM_CTX,
                            timeout=TIMEOUT_SECONDS)
        entry["stats"] = stats
    except Exception as error:  # noqa: BLE001
        entry["error"] = f"{type(error).__name__}: {error}"
    entry["wall_s"] = round(time.monotonic() - started, 3)
    print(f"[prime] {family} {entry.get('stats') or entry.get('error')} "
          f"{entry['wall_s']}s", flush=True)
    return entry


def run() -> dict:
'''
assert "\n\ndef run() -> dict:\n" in src
src = src.replace("\n\ndef run() -> dict:\n", helpers, 1)

open(path, "w", encoding="utf-8").write(src)
py_compile.compile(path, doraise=True)
print("patched + compiled OK:", path)
