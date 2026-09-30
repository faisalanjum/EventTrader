"""Throughput probe (JEV.md §9.1 task 9): how many Jev calls per minute do we really get? Sends the 5-short-tag call (~1,100 tokens) from N threads
for SECS seconds and counts successes, HTTP 429s and other errors, WITHOUT retrying. Prints the response headers of one call.
Usage: python3 probe_rate.py <threads> <seconds>"""
import json, sys, time, threading, urllib.request, urllib.error, collections
sys.path.insert(0, ".")
import prompts_v3 as P
from sweep_corpus import SET_B
THREADS, SECS = int(sys.argv[1]), int(sys.argv[2])
STATE = {"where_it_appears": "Management's Discussion and Analysis of a quarterly report (10-Q)",
         "text_before_quote": "Revenue for the quarter was affected by lower volumes. We continue to invest in capacity and expect margins to recover in the second half.",
         "quote": "Net sales increased 5% to $2.1 billion compared with the prior-year quarter, ahead of the consensus estimate of $2.0 billion.",
         "text_after_quote": "Adjusted earnings per share were $1.20."}
BODY = json.dumps({"state": STATE, "model": "jev-1.13.0", "questions": SET_B}).encode()
cnt = collections.Counter(); lat = []; lock = threading.Lock(); stop = time.time() + SECS; toks = [0]
def worker():
    while time.time() < stop:
        t0 = time.time()
        try:
            req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", BODY, {"Authorization": "Bearer " + P.KEY, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.load(r); h = dict(r.headers)
            with lock: cnt["ok"] += 1; lat.append(time.time() - t0); toks[0] += d["usage"]["input_tokens"]; cnt["hdr"] = h if "hdr" not in cnt else cnt["hdr"]
        except urllib.error.HTTPError as e:
            with lock: cnt[f"HTTP {e.code}"] += 1
            time.sleep(0.5)
        except Exception as e:
            with lock: cnt["other"] += 1
ts = [threading.Thread(target=worker) for _ in range(THREADS)]
t0 = time.time(); [t.start() for t in ts]; [t.join() for t in ts]; el = time.time() - t0
hdr = cnt.pop("hdr", None)
lat.sort()
print(f"threads {THREADS}: {el:.0f}s | ok {cnt['ok']} = {cnt['ok']/el*60:,.0f} calls/min | 429s {cnt['HTTP 429']} | other errors { {k:v for k,v in cnt.items() if k not in ('ok',)} } | median latency {lat[len(lat)//2]:.2f}s p95 {lat[int(.95*len(lat))]:.2f}s | tokens/s {toks[0]/el:,.0f} | cost ${toks[0]*0.042/1e6:.3f}")
if hdr and THREADS == 4: print("response headers:", {k: v for k, v in hdr.items() if k.lower().startswith(("x-", "retry", "ratelimit", "content-type", "server", "via"))})
