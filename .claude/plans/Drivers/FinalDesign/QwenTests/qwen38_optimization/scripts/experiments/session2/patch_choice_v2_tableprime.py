#!/usr/bin/env python3
"""Upgrade the shadow choice_v2.py priming from FAMILY level to TABLE level.
Families that share a table differ only after the 'TARGET FOR THIS CALL:' line
(different Known-Driver line), so priming the table-level prefix once serves
every family on that table. Usage: patch_choice_v2_tableprime.py <choice_v2.py>"""
import sys, shutil, time, py_compile
path = sys.argv[1]
src = open(path, encoding="utf-8").read()
if "_prime_key" in src:
    print("already patched"); sys.exit(0)
bak = f"{path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copy2(path, bak); print("backup:", bak)

old_loop = '''    families = {}
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
assert old_loop in src, "family-prime loop not found"
new_loop = '''    prime_log = []
    primed_keys = set()

    mode = "a" if RAW_RESULTS_PATH.exists() else "x"
    with RAW_RESULTS_PATH.open(mode, encoding="utf-8") as handle:
        for number, case in enumerate(pending, 1):
            key = _prime_key(case)
            if PRIME_PREFIX and key not in primed_keys:
                primed_keys.add(key)
                prime_log.append(_prime_table(_family_of(case), key))
            result = run_one(case)
'''
src = src.replace(old_loop, new_loop, 1)

old_helper_start = '''def _prime_family(family: str, prompts: list[str]) -> dict:'''
assert old_helper_start in src
new_helpers = '''PRIME_MARKER = "TARGET FOR THIS CALL:" + chr(10)


def _prime_key(case: dict) -> str:
    """TABLE-level shared prefix: everything up to and including the
    'TARGET FOR THIS CALL:' line. Families on the same table are byte-identical
    up to here and differ only in the Known-Driver / Requested-cell lines, so
    ONE prime per table serves every family on it (measured 2026-08-16: with
    family-level priming the second family on a table still re-prefilled the
    whole table - log 'matched=6172 cached=152')."""
    prompt = case["prompt"]
    i = prompt.find(PRIME_MARKER)
    if i < 0:
        return prompt  # no marker: prime the whole prompt (harmless)
    return prompt[: i + len(PRIME_MARKER)]


def _prime_table(family: str, prefix: str) -> dict:
    """Prime the server prefix cache with one table-level prefix. Never fails
    the run: priming is a pure cache warm-up (output discarded, no case prompt
    changes)."""
    started = time.monotonic()
    entry = {"first_family": family, "prefix_chars": len(prefix)}
    try:
        entry["stats"] = L.prime(prefix, SYSTEM_MESSAGE, num_ctx=NUM_CTX,
                                 timeout=TIMEOUT_SECONDS, with_stats=True)
    except Exception as error:  # noqa: BLE001
        entry["error"] = f"{type(error).__name__}: {error}"
    entry["wall_s"] = round(time.monotonic() - started, 3)
    print(f"[prime] table@{family} {entry.get('stats') or entry.get('error')} "
          f"{entry['wall_s']}s", flush=True)
    return entry


def _prime_family(family: str, prompts: list[str]) -> dict:'''
src = src.replace(old_helper_start, new_helpers, 1)
open(path, "w", encoding="utf-8").write(src)
py_compile.compile(path, doraise=True)
print("patched + compiled OK:", path)
