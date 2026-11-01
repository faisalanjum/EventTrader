"""Preflight: prove every structural guarantee of the inference pipeline.
Run from the Minisforum:  python3 config/preflight.py
Exit 0 = all green. Model-agnostic; does NOT test any task/answer-key."""
import sys
import time

sys.path.insert(0, "/home/faisal/EventMarketDB")
from config import local_llm as L  # noqa: E402

PASS, FAIL = "PASS", "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((cond, name, detail))
    print(f"  [{PASS if cond else FAIL}] {name}" + (f"  — {detail}" if detail else ""))


print("=" * 70)
h = L.health()
print(f"host={h.get('host')}  version={h.get('version')}  model={h.get('model')}")
print(f"num_ctx={h.get('num_ctx')}  input_token_budget={h.get('input_token_budget')}")
print(f"loaded={h.get('loaded')}")
print("=" * 70)

# 1. reachability + right model resident
check("server reachable", "error" not in h)
check("target model resident", h.get("model") in (h.get("loaded") or []))

# 2. basic completion + speed
t = time.time()
txt, st = L.generate("Reply with exactly: OK", with_stats=True)
check("basic completion", "OK" in txt, f"{time.time()-t:.2f}s @ {st['tok_s']} tok/s")
check("done_reason surfaced", st["done_reason"] == "stop", f"done_reason={st['done_reason']}")

# 3. determinism (temp=0)
outs = [L.generate("Name 5 US restaurant chains, comma-separated, nothing else.")
        for _ in range(3)]
check("determinism (3x identical)", len(set(o.strip() for o in outs)) == 1)

# 4. unicode round-trip
u = "Café’s Q3 rose 12%—€5.2M; “traffic” fell 2%. Piña ✓"
got = L.generate(f"Repeat EXACTLY, nothing else:\n{u}")
check("unicode round-trip", u in got)

# 5. structured output (schema-enforced JSON)
schema = {"type": "object",
          "properties": {"ticker": {"type": "string"}, "value": {"type": "number"}},
          "required": ["ticker", "value"], "additionalProperties": False}
try:
    obj = L.structured("McDonald's Q3 revenue was 6.9 billion. Give ticker and value.",
                       schema)
    ok = isinstance(obj, dict) and "ticker" in obj and "value" in obj
    check("structured JSON (schema)", ok, str(obj))
except Exception as e:  # noqa: BLE001
    check("structured JSON (schema)", False, str(e)[:80])

# 6. nested-list schema (realistic extraction shape)
nested = {"type": "object", "properties": {
    "items": {"type": "array", "items": {"type": "object", "properties": {
        "name": {"type": "string"}, "n": {"type": "integer"}},
        "required": ["name", "n"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False}
try:
    obj = L.structured("Apple made 3 phones and Ford made 5 cars. List them.", nested)
    check("nested-list schema", isinstance(obj.get("items"), list) and len(obj["items"]) >= 1,
          str(obj)[:90])
except Exception as e:  # noqa: BLE001
    check("nested-list schema", False, str(e)[:80])

# 7. INPUT truncation is caught (must RAISE, not silently cut)
big = "IMPORTANT_RULE_AT_TOP. " + " ".join(f"w{i:05d}" for i in range(12000)) + " end."
raised = False
try:
    L.generate(big + " Echo the first token.", num_ctx=8192)
except L.TruncatedInputError:
    raised = True
except Exception as e:  # noqa: BLE001
    raised = f"wrong-exc:{type(e).__name__}"
check("input truncation RAISES (no silent cut)", raised is True, f"raised={raised}")

# 8. allow_truncation escape hatch works
try:
    L.generate(big, num_ctx=8192, allow_truncation=True, max_tokens=5)
    check("allow_truncation bypass", True)
except Exception as e:  # noqa: BLE001
    check("allow_truncation bypass", False, str(e)[:60])

# 9. OUTPUT truncation surfaced via stats
_, st2 = L.generate("Write 500 words about restaurants.", max_tokens=12, with_stats=True)
check("output-cut visible (done_reason=length)", st2["truncated_output"] is True,
      f"done_reason={st2['done_reason']}")

# 10. concurrency correctness (4 parallel, distinct answers)
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
qs = ["Reply with exactly: A", "Reply with exactly: B",
      "Reply with exactly: C", "Reply with exactly: D"]
t = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    r = list(ex.map(lambda q: L.generate(q).strip(), qs))
check("4x concurrency correctness", [x[-1] for x in r] == ["A", "B", "C", "D"],
      f"{time.time()-t:.1f}s -> {r}")

# 11. host failover (bad primary -> mDNS)
import importlib  # noqa: E402
import os  # noqa: E402
os.environ["LOCAL_LLM_HOST"] = "http://10.255.255.1:11434"
importlib.reload(L)
t = time.time()
try:
    o = L.generate("Reply with exactly: FAILOVER", timeout=40)
    check("host failover", "FAILOVER" in o, f"{time.time()-t:.1f}s via {L.resolve_host()}")
except Exception as e:  # noqa: BLE001
    check("host failover", False, str(e)[:60])
os.environ.pop("LOCAL_LLM_HOST", None)
importlib.reload(L)

print("=" * 70)
n_fail = sum(1 for ok, _, _ in results if not ok)
print(f"{'ALL GREEN' if n_fail == 0 else str(n_fail) + ' FAILED'}: "
      f"{len(results)-n_fail}/{len(results)} checks passed")
sys.exit(1 if n_fail else 0)
