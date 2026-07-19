#!/usr/bin/env python3
# Liquid trackers feed puller for EventTrader. Stdlib only.
# Source: api.liquidmax.xyz (Liquid Co-Invest backend) — undocumented, public, no-auth.
# ~100-event rolling buffer, NO backfill -> poll continuously, persist last seq, dedup on seq.
# Enrichment fields are usually empty; tickers_naive is a placeholder (do real NER downstream).
import argparse, json, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://api.liquidmax.xyz"
FEED, ROSTER = BASE + "/api/trackers/feed", BASE + "/api/trackers/roster"
FOLDER = Path(__file__).resolve().parent
STATE, OUT = FOLDER / ".trackers_state.json", FOLDER / "trackers_events.jsonl"
CASHTAG = re.compile(r"\$([A-Z]{1,5})\b")

def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"Accept": "application/json",
                                               "User-Agent": "eventtrader-trackers/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {"last_seq": 0}

def tickers(ev):  # placeholder — replace with EventTrader NER + driver-ontology mapping
    return sorted(set(CASHTAG.findall(str(ev.get("payload", "")))))

def velocity(evts):
    v = {}
    for e in evts:
        for t in tickers(e):
            v.setdefault(t, set()).add(e.get("subject"))
    return v

def pull_once(verbose=True):
    st = load_state(); last = int(st.get("last_seq", 0))
    try:
        evts = _get(FEED).get("events", [])
    except urllib.error.HTTPError as e:
        print(f"[trackers] HTTP {e.code} — endpoint may have changed/auth-gated.", file=sys.stderr); return []
    except Exception as e:
        print(f"[trackers] fetch failed: {e}", file=sys.stderr); return []
    for e in evts:
        try:
            e["_s"] = int(e.get("seq"))
        except (TypeError, ValueError):
            e["_s"] = -1
    evts = sorted((e for e in evts if e["_s"] >= 0), key=lambda e: e["_s"])
    new = [e for e in evts if e["_s"] > last]
    if last and new and min(e["_s"] for e in new) > last + 1:
        print(f"[trackers] WARNING: ~{min(e['_s'] for e in new)-last-1} events missed "
              f"(buffer rolled). Poll more frequently.", file=sys.stderr)
    if new:
        mx = max(e["_s"] for e in new)
        with open(OUT, "a") as f:
            for e in new:
                e["tickers_naive"] = tickers(e); e.pop("_s", None)
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        st["last_seq"] = mx
        with open(STATE, "w") as f:
            json.dump(st, f)
    if verbose:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        if new:
            hot = ", ".join(f"${t}x{len(s)}" for t, s in
                            sorted(velocity(new).items(), key=lambda kv: -len(kv[1]))[:5] if s)
            print(f"[{ts}] +{len(new)} new (last_seq={st['last_seq']})" + (f" | hot: {hot}" if hot else ""))
        else:
            print(f"[{ts}] no new events (last_seq={last})")
    return new

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true"); ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=25); ap.add_argument("--roster", action="store_true")
    a = ap.parse_args()
    if a.roster:
        for x in sorted(_get(ROSTER).get("roster", []), key=lambda x: (x.get("source",""), x.get("subject",""))):
            print(f"{x.get('source','?'):>12} {x.get('subject',''):<22} "
                  f"{(x.get('meta') or {}).get('display_name',''):<22} {x.get('status','')}")
        return
    if a.loop:
        print(f"[trackers] looping every {a.interval}s — Ctrl-C to stop.", file=sys.stderr)
        try:
            while True:
                pull_once(); time.sleep(a.interval)
        except KeyboardInterrupt:
            print("\n[trackers] stopped.", file=sys.stderr)
    else:
        pull_once()

if __name__ == "__main__":
    main()
