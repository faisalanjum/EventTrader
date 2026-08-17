#!/usr/bin/env python3
"""Patch the SHADOW qf01.py (aligned 5x50 contract) for prefix caching:
  - rendered_table BEFORE anchor in the model input (shared table first)
  - sequential run grouped by table with one prime per table (WORKERS=1)
  - MODEL back to qwen3.8:27b-mlx, TIMEOUT 1800, NUM_CTX from QWEN_NUM_CTX
Usage: python3 patch_qf01_prime.py <path/to/qf01.py>"""
import sys, shutil, time, py_compile
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
if "PRIME_PREFIX" in src:
    print("already patched"); sys.exit(0)
bak = f"{path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(path, bak); print("backup:", bak)

old = ('NUM_CTX = 16384\nMAX_TOKENS = 512\nTIMEOUT_SECONDS = 300\nWORKERS = 4\n'
       'MODEL_NAME = "qwen3.8:27b-mtp-q4_K_M"\n')
assert old in src, "constants block not found"
new = ('NUM_CTX = int(os.environ.get("QWEN_NUM_CTX", "16384"))  # frozen at prepare\n'
       'MAX_TOKENS = 512\n'
       'TIMEOUT_SECONDS = 1800   # cold prefill of a 12k-char table can exceed 300 s\n'
       'WORKERS = 1              # sequential, grouped by table: prefix cache + priming\n'
       'MODEL_NAME = "qwen3.8:27b-mlx"\n'
       '# Prefix priming per table (QWEN_PRIME=0 disables) - see config/local_llm.py prime()\n'
       'PRIME_PREFIX = os.environ.get("QWEN_PRIME", "1") != "0"\n')
src = src.replace(old, new, 1)

old_in = '                model_input = {"anchor": anchor, "rendered_table": rendered}\n'
assert old_in in src
new_in = ('                # PREFIX-CACHE ORDERING (2026-08-16): the table (shared by every\n'
          '                # anchor on it) goes FIRST and the per-call anchor LAST, so the\n'
          '                # server KV prefix is reused across the table\'s calls. Same JSON\n'
          '                # content, same keys; only the key order changes.\n'
          '                model_input = {"rendered_table": rendered, "anchor": anchor}\n')
src = src.replace(old_in, new_in, 1)

old_loop = '''    with RAW_RESULTS_PATH.open("x", encoding="utf-8") as output_file:
        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {
                executor.submit(run_one, case): case for case in cases
            }
            for number, future in enumerate(as_completed(futures), 1):
                result = future.result()
                output_file.write(
'''
assert old_loop in src, "run loop not found"
new_loop = '''    # Sequential, grouped by table, one prime per table (see PRIME_PREFIX).
    ordered = sorted(cases, key=lambda c: (c.get("table_id") or "", c["id"]))
    prime_log = []
    last_table = None

    def _results():
        nonlocal last_table
        for case in ordered:
            table = case.get("table_id")
            if PRIME_PREFIX and table != last_table:
                prompts = [c["prompt"] for c in ordered if c.get("table_id") == table]
                t0 = time.monotonic()
                entry = {"table": table, "cases": len(prompts)}
                try:
                    entry["stats"] = L.prime_for(prompts, None, num_ctx=NUM_CTX,
                                                 timeout=TIMEOUT_SECONDS)
                except Exception as error:  # noqa: BLE001
                    entry["error"] = f"{type(error).__name__}: {error}"
                entry["wall_s"] = round(time.monotonic() - t0, 3)
                print(f"[prime] {table} {entry.get('stats') or entry.get('error')} "
                      f"{entry['wall_s']}s", flush=True)
                prime_log.append(entry)
            last_table = table
            yield run_one(case)

    with RAW_RESULTS_PATH.open("x", encoding="utf-8") as output_file:
        if True:
            for number, result in enumerate(_results(), 1):
                output_file.write(
'''
src = src.replace(old_loop, new_loop, 1)

old_rec = '''        "model_before": manifest["model"],
        "model_after": model_fingerprint(),
        "scored": False,
    }
    if record["model_after"] != record["model_before"]:
        raise RuntimeError("model changed during the run")
'''
assert old_rec in src
new_rec = '''        "model_before": manifest["model"],
        "model_after": model_fingerprint(),
        "prefix_priming": PRIME_PREFIX,
        "prime_calls": prime_log,
        "scored": False,
    }
    if record["model_after"] != record["model_before"]:
        raise RuntimeError("model changed during the run")
'''
src = src.replace(old_rec, new_rec, 1)
open(path, "w", encoding="utf-8").write(src)
py_compile.compile(path, doraise=True)
print("patched + compiled OK:", path)
