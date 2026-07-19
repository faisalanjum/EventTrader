#!/usr/bin/env python3
# Hyperliquid 'xyz' dex (Liquid) market-data puller — free, no-auth, 24/7 cross-asset.
# Fills IBKR gaps: overnight/weekend pricing + macro/commodity/FX/global-index coverage
# that IBKR charges per-exchange for. Snapshot + funding history + OHLCV candles + book.
import argparse, json, sys, time, urllib.request
from datetime import datetime, timezone

API = "https://api.hyperliquid.xyz/info"

def _post(body, timeout=20):
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "et-xyz/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

GROUPS = {
 'commodity': {'GOLD','SILVER','COPPER','PLATINUM','PALLADIUM','CL','BRENTOIL',
               'NATGAS','ALUMINIUM','CORN','WHEAT','TTF','URANIUM'},
 'fx':        {'EUR','JPY','GBP','KRW','NOK','DXY'},
 'index':     {'SP500','XYZ100','JP225','NIFTY','IBOV','KR200','VIX','VOL'},
 'etf':       {'EWY','EWJ','EWZ','EWT','SMH','XLE','URNM','USAR','H100','DRAM'},
 'crypto':    {'BTC','ETH','SOL','XRP','QNT','BIRD','BOT','PURRDAT'},
}
def group_of(s):
    for g, m in GROUPS.items():
        if s in m: return g
    return 'stock'

def _f(x):
    try: return float(x)
    except (TypeError, ValueError): return 0.0

def snapshot():
    d = _post({"type": "metaAndAssetCtxs", "dex": "xyz"})
    uni, ctxs = d[0]['universe'], d[1]
    out = []
    for u, c in zip(uni, ctxs):
        s = u['name'].replace('xyz:', '')
        out.append({'sym': s, 'group': group_of(s), 'mark': _f(c.get('markPx')),
                    'funding': _f(c.get('funding')), 'oi': _f(c.get('openInterest')),
                    'vol': _f(c.get('dayNtlVlm')), 'lev': u.get('maxLeverage')})
    return out

def funding_history(coin, hours=72):
    start = int((time.time() - hours * 3600) * 1000)
    return _post({"type": "fundingHistory", "coin": f"xyz:{coin}", "startTime": start})

def candles(coin, interval="1h", hours=72):
    now = int(time.time() * 1000)
    return _post({"type": "candleSnapshot", "req": {"coin": f"xyz:{coin}",
                  "interval": interval, "startTime": now - hours*3600*1000, "endTime": now}})

def main():
    ap = argparse.ArgumentParser(description="Hyperliquid xyz-dex market data.")
    ap.add_argument("--snapshot", action="store_true", help="all markets (default)")
    ap.add_argument("--macro", action="store_true", help="only commodity/fx/index/etf, live only")
    ap.add_argument("--live-only", action="store_true", help="filter to vol>0")
    ap.add_argument("--funding", metavar="SYM", help="funding history for SYM (e.g. GOLD)")
    ap.add_argument("--candles", metavar="SYM", help="OHLCV for SYM")
    ap.add_argument("--interval", default="1h"); ap.add_argument("--hours", type=int, default=72)
    ap.add_argument("--jsonl", metavar="PATH", help="append snapshot to JSONL")
    a = ap.parse_args()

    if a.funding:
        for r in funding_history(a.funding, a.hours): print(json.dumps(r))
        return
    if a.candles:
        for r in candles(a.candles, a.interval, a.hours): print(json.dumps(r))
        return

    rows = snapshot()
    if a.macro:
        rows = [r for r in rows if r['group'] in ('commodity', 'fx', 'index', 'etf')]
    if a.macro or a.live_only:
        rows = [r for r in rows if r['vol'] > 0]
    rows.sort(key=lambda r: (r['group'], -r['vol']))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    print(f"# xyz-dex snapshot {ts}  ({len(rows)} markets, * = live)")
    print(f"{'sym':<12}{'group':<11}{'mark':>13}{'funding/hr':>13}{'dayVol$':>16}")
    for r in rows:
        live = '*' if r['vol'] > 0 else ' '
        print(f"{r['sym']:<11}{live}{r['group']:<11}{r['mark']:>13.6g}{r['funding']:>13.6f}{r['vol']:>16,.0f}")
    if a.jsonl:
        with open(a.jsonl, "a") as f:
            f.write(json.dumps({"ts": ts, "rows": rows}) + "\n")
        print(f"\n[appended -> {a.jsonl}]", file=sys.stderr)

if __name__ == "__main__":
    main()
