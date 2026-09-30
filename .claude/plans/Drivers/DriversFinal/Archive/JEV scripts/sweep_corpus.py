"""Whole-corpus sweep estimate (JEV.md §9.1 task 9): how many calls, tokens, dollars and days to send every sentence and table row of
every filing, transcript and news story to Jev with 5 questions per call. Read-only on Neo4j.
Stage 1  `python3 sweep_corpus.py units`   exact character totals per text pool (Neo4j aggregates) + a stratified sample of documents,
         split into UNITS with split_units() -> units per character with a bootstrap 95% interval per pool. Saves sweep_units_stats.json (repo)
         and sweep_units_sample.pkl (scratchpad; contains filing text, do not commit).
Stage 2  `python3 sweep_corpus.py tokens`  real Jev calls on sampled units (5 short tags; and the 5 full fact-card questions) -> tokens per call
         per group, then the final table. Needs stage 1. Use /home/faisal/EventMarketDB/venv/bin/python3 (neo4j driver).
UNIT = one sentence, or one table row (a label plus the numbers after it), capped at CAP characters (a flattened table run-on is cut at CAP)."""
import os, re, json, random, statistics, sys, collections, pickle, time
sys.path.insert(0, ".")
import jevlib as J

SCRATCH = "/tmp/claude-1000/-home-faisal-EventMarketDB/7e6a5492-bcab-436c-8470-48a87eb77533/scratchpad"
PKL = f"{SCRATCH}/sweep_units_sample.pkl"
PARA = bool(os.environ.get("SWEEP_PARA"))          # paragraph mode: also pack units into paragraph chunks (writes sweep_paragraph_stats.json)
PKL_PARA = f"{SCRATCH}/sweep_para_sample.pkl"
CAP = int(os.environ.get("SWEEP_CAP", 1000))     # base case 1000; other values only for the sensitivity check
random.seed(2026)

# ------------------------------------------------------------------ splitter
NOLETTER = re.compile(r"^[^A-Za-z]*$")            # a block with no letters: numbers, $, %, brackets = a table cell
def _chunks(t, cap=CAP):
    t = t.strip()
    while len(t) > cap:
        k = t.rfind(" ", 0, cap); k = k if k > cap * 0.5 else cap
        yield t[:k].strip(); t = t[k:].strip()
    if t: yield t

def split_units(text, marks=False):
    """marks=True also emits None between real paragraphs, and between a run of table rows and prose (used by pack)."""
    text = text.replace("##TABLE_START", "\n\n").replace("##TABLE_END", "\n\n")
    out, row, last = [], None, None
    def flush():
        nonlocal row
        if row: out.extend(_chunks(" ".join(row))); row = None
    for p in re.split(r"\n\s*\n", text):
        p = " ".join(p.split())
        if not p: continue
        if NOLETTER.match(p) or (len(p) <= 60 and not re.search(r"[.!?][\"”’)]?$", p)):
            if marks and last == "prose": out.append(None)
            last = "row"
            if NOLETTER.match(p): row = (row or []) + [p]           # numeric cell: joins the current row
            else: flush(); row = [p]                                  # short label: starts a row
            continue
        flush()
        if marks and last == "row": out.append(None)
        last = "prose"
        for sent in J.SENT_END.split(p):
            if sent.strip(): out.extend(_chunks(sent))
        if marks: out.append(None)
    flush()
    return out

def pack(marked, maxc=1200, minc=200):
    """Paragraph chunks: a real paragraph stays whole (merged with the next one while under minc characters); anything longer than maxc is cut at a
    sentence boundary; a table's rows and flat text (no paragraph breaks at all) are packed sentence by sentence up to maxc. Returns [(text, n_units)]."""
    out, buf, n = [], [], 0
    def flush():
        nonlocal buf, n
        if buf: out.append((" ".join(buf), len(buf))); buf, n = [], 0
    for u in marked:
        if u is None:
            if n >= minc: flush()
            continue
        if n and n + len(u) + 1 > maxc: flush()
        buf.append(u); n += len(u) + 1
    flush()
    return out

# ------------------------------------------------------------------ neo4j
def connect():
    from neo4j import GraphDatabase
    env = dict(l.strip().split("=", 1) for l in open("/home/faisal/EventMarketDB/.env") if re.match(r"^NEO4J_(URI|USERNAME|PASSWORD)=", l))
    return GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USERNAME"], env["NEO4J_PASSWORD"].strip("'\"")))

FS_NAMES = {"FinancialStatementsandSupplementaryData", "ExhibitsandFinancialStatementSchedules", "FinancialStatements"}
def exhibit_group(n):
    n = n or ""
    if n == "EX-99.1": return "EX-99.1"
    if n.startswith("EX-99"): return "EX-99.other"
    if n.startswith("EX-10"): return "EX-10"
    return "EX-other"

def units_stage():
    drv = connect()
    def q(cy, **p):
        with drv.session(default_access_mode="READ") as s: return s.run(cy, **p).data()
    strata = []          # dicts: name, group, total_chars, fetch (callable -> [(id,text)]), n
    # ---- sections
    rows = q("MATCH (s:ExtractedSectionContent) RETURN s.form_type AS f, s.section_name AS n, count(*) AS c, sum(size(s.content)) AS ch")
    byform = collections.defaultdict(list)
    for r in rows: byform[r["f"]].append(r)
    for f, rs in byform.items():
        tot = sum(r["ch"] for r in rs)
        if tot == 0: continue
        big = [r for r in rs if r["ch"] >= 0.03 * tot]; small = [r for r in rs if r["ch"] < 0.03 * tot]
        for r in big:
            strata.append(dict(name=f"sec|{f}|{r['n'][:40]}", group="FS sections" if r["n"] in FS_NAMES else "prose sections", chars=r["ch"], kind="sec", f=f, names=[r["n"]], n=40))
        if small:
            strata.append(dict(name=f"sec|{f}|other", group="prose sections", chars=sum(r["ch"] for r in small), kind="sec_other", f=f, names=[r["n"] for r in big], n=30))
    # ---- exhibits
    rows = q("MATCH (e:ExhibitContent) RETURN e.exhibit_number AS n, count(*) AS c, sum(size(e.content)) AS ch")
    g = collections.Counter()
    for r in rows: g[exhibit_group(r["n"])] += r["ch"]
    for name, ch in g.items():
        strata.append(dict(name=f"exh|{name}", group={"EX-99.1": "press release exhibits", "EX-99.other": "press release exhibits", "EX-10": "contract exhibits", "EX-other": "other exhibits"}[name], chars=ch, kind="exh", ex=name, n=60))
    # ---- filing text that is the ONLY text of its filing (425, 13D ...); on 8-K/10-Q/10-K it duplicates sections+exhibits and is excluded
    ft = q("MATCH (r:Report)-[]->(f:FilingTextContent) WHERE NOT (r)-[]->(:ExtractedSectionContent) AND NOT (r)-[]->(:ExhibitContent) RETURN count(f) AS c, sum(size(f.content)) AS ch")[0]
    strata.append(dict(name="filing text only (425, 13D, ...)", group="filing text only", chars=ft["ch"], kind="ft", n=40))
    # ---- transcripts and news
    pr = q("MATCH (p:PreparedRemark) RETURN count(*) AS c, sum(size(p.content)) AS ch")[0]
    strata.append(dict(name="prepared remarks", group="prepared remarks", chars=pr["ch"], kind="pr", n=60))
    qa = q("MATCH (x:QAExchange) RETURN count(*) AS c, sum(size(x.exchanges)) AS ch")[0]
    strata.append(dict(name="Q&A exchanges (json chars)", group="Q&A", chars=qa["ch"], kind="qa", n=100, json=True))
    nb = q("MATCH (n:News) WHERE size(coalesce(n.body,''))>0 RETURN count(*) AS c, sum(size(n.body)) AS ch")[0]
    strata.append(dict(name="news bodies", group="news bodies", chars=nb["ch"], kind="news", n=250))
    news_titles = q("MATCH (n:News) RETURN count(*) AS c, sum(size(coalesce(n.title,''))) AS ch")[0]
    print("exact totals: filing-text-only", ft, "| remarks", pr, "| qa", qa, "| news bodies", nb, "| news titles", news_titles)

    def fetch(st):
        k = st["kind"]; n = st["n"]
        with drv.session(default_access_mode="READ") as s:
            if k == "sec": cy, p = "MATCH (s:ExtractedSectionContent) WHERE s.form_type=$f AND s.section_name IN $names AND size(s.content)>0 WITH s, rand() AS r ORDER BY r LIMIT $n RETURN s.id AS id, s.content AS text", dict(f=st["f"], names=st["names"], n=n)
            elif k == "sec_other": cy, p = "MATCH (s:ExtractedSectionContent) WHERE s.form_type=$f AND NOT s.section_name IN $names AND size(s.content)>0 WITH s, rand() AS r ORDER BY r LIMIT $n RETURN s.id AS id, s.content AS text", dict(f=st["f"], names=st["names"], n=n)
            elif k == "exh":
                cond = {"EX-99.1": "e.exhibit_number = 'EX-99.1'", "EX-99.other": "e.exhibit_number STARTS WITH 'EX-99' AND e.exhibit_number <> 'EX-99.1'", "EX-10": "e.exhibit_number STARTS WITH 'EX-10'", "EX-other": "NOT e.exhibit_number STARTS WITH 'EX-99' AND NOT e.exhibit_number STARTS WITH 'EX-10'"}[st["ex"]]
                cy, p = f"MATCH (e:ExhibitContent) WHERE {cond} AND size(e.content)>0 WITH e, rand() AS r ORDER BY r LIMIT $n RETURN e.id AS id, e.content AS text", dict(n=n)
            elif k == "ft": cy, p = "MATCH (r:Report)-[]->(f:FilingTextContent) WHERE NOT (r)-[]->(:ExtractedSectionContent) AND NOT (r)-[]->(:ExhibitContent) WITH f, rand() AS r ORDER BY r LIMIT $n RETURN f.id AS id, f.content AS text", dict(n=n)
            elif k == "pr": cy, p = "MATCH (p:PreparedRemark) WITH p, rand() AS r ORDER BY r LIMIT $n RETURN p.id AS id, p.content AS text", dict(n=n)
            elif k == "qa": cy, p = "MATCH (x:QAExchange) WITH x, rand() AS r ORDER BY r LIMIT $n RETURN x.id AS id, x.exchanges AS text", dict(n=n)
            elif k == "news": cy, p = "MATCH (n:News) WHERE size(coalesce(n.body,''))>0 WITH n, rand() AS r ORDER BY r LIMIT $n RETURN n.id AS id, n.title AS title, n.body AS text", dict(n=n)
            return s.run(cy, **p).data()

    out = []
    for st in strata:
        t0 = time.time(); docs = fetch(st)
        recs = []
        for d in docs:
            text = d["text"] or ""
            if st.get("json"):
                try: turns = json.loads(text)
                except Exception: turns = []
                body = "\n\n".join(t.get("text", "") for t in turns); jchars = len(text)
                marked = [x for t in turns for x in (split_units(t.get("text", ""), marks=True) + [None])]
                rec = dict(id=d["id"], chars=jchars, textchars=len(body))
            else:
                marked = split_units(text, marks=True)
                rec = dict(id=d["id"], chars=len(text), text_len=len(text))
            rec["units"] = [u for u in marked if u is not None]
            if PARA: rec["paras"] = {m: pack(marked, m) for m in (600, 1200, 2500)}
            recs.append(rec)
        # ratio estimator: units per character (chars = the same measure as the exact totals)
        U = [len(r["units"]) for r in recs]; C = [r["chars"] for r in recs]
        ratio = sum(U) / max(1, sum(C))
        boots = []
        for _ in range(400):
            idx = [random.randrange(len(recs)) for _ in recs]
            boots.append(sum(U[i] for i in idx) / max(1, sum(C[i] for i in idx)))
        boots.sort(); lo, hi = boots[10], boots[389]
        ul = [len(u) for r in recs for u in r["units"]]
        pstats = {}
        if PARA:
            for m in (600, 1200, 2500):
                PC = [len(r["paras"][m]) for r in recs]; rr = sum(PC) / max(1, sum(C)); bb = []
                for _ in range(400):
                    idx = [random.randrange(len(recs)) for _ in recs]; bb.append(sum(PC[i] for i in idx) / max(1, sum(C[i] for i in idx)))
                bb.sort(); pstats[m] = dict(est=rr * st["chars"], ci=[bb[10] * st["chars"], bb[389] * st["chars"]], units_per_chunk=sum(len(r["units"]) for r in recs) / max(1, sum(PC)),
                                            mean_chars=statistics.mean([len(t) for r in recs for t, _ in r["paras"][m]]) if any(r["paras"][m] for r in recs) else 0)
        st2 = dict(name=st["name"], group=st["group"], total_chars=st["chars"], docs=len(recs), sample_chars=sum(C), sample_units=sum(U),
                   units_per_char=ratio, ci=[lo, hi], est_calls=ratio * st["chars"], est_calls_ci=[lo * st["chars"], hi * st["chars"]],
                   mean_unit_chars=statistics.mean(ul) if ul else 0, median_unit_chars=statistics.median(ul) if ul else 0)
        if PARA: st2["para"] = pstats
        if st.get("json"): st2["text_over_json"] = sum(r["textchars"] for r in recs) / max(1, sum(C))
        out.append((st2, recs))
        print(f"{st['name'][:52]:52s} docs {len(recs):3d} units/char {ratio:.5f}  chars/unit {1/ratio if ratio else 0:6.0f}  est calls {ratio*st['chars']/1e6:8.2f}M  [{lo*st['chars']/1e6:.2f}-{hi*st['chars']/1e6:.2f}]  ({time.time()-t0:.0f}s)", flush=True)
    # news titles: exactly one unit per story
    out.append((dict(name="news titles", group="news titles", total_chars=news_titles["ch"], docs=0, est_calls=float(news_titles["c"]), est_calls_ci=[float(news_titles["c"])] * 2, mean_unit_chars=news_titles["ch"] / news_titles["c"], units_per_char=news_titles["c"] / news_titles["ch"]), []))
    stats = [s for s, _ in out]
    if PARA:
        json.dump(stats, open("sweep_paragraph_stats.json", "w"), indent=1); pickle.dump(out, open(PKL_PARA, "wb"))
        print("paragraph chunks (est, M):", {m: round(sum(s["para"][m]["est"] for s in stats if "para" in s) / 1e6 + 0.35, 2) for m in (600, 1200, 2500)}, "(+0.35M headlines)")
    elif CAP == 1000:
        json.dump(stats, open("sweep_units_stats.json", "w"), indent=1)
        pickle.dump(out, open(PKL, "wb"))
    print("\nTOTAL est calls %.1fM" % (sum(s["est_calls"] for s in stats) / 1e6))

# ------------------------------------------------------------------ stage 2: real tokens per call, then the totals
WHERE = {"prose sections": "Management's Discussion and Analysis of a quarterly report (10-Q)", "FS sections": "Financial Statements of a quarterly report (10-Q)",
         "press release exhibits": "earnings press release (Exhibit 99.1)", "contract exhibits": "agreement exhibit (Exhibit 10.1)",
         "filing text only": "merger communication (Schedule 425)", "prepared remarks": "earnings call prepared remarks", "Q&A": "earnings call question and answer",
         "news bodies": "news story", "news titles": "news headline"}
PRICE = 0.042 / 1e6
READ_S = "Judge `quote`. `text_before_quote` and `text_after_quote` are the text around it; use them only to see what `quote` refers to."
def _yn(qq, yes, no): return {"type": "noul", "instructions": {"question": qq, "read": READ_S}, "criteria": {"true": {"what": yes}, "false": {"what": no}}}
SET_B = {   # five short tags, no driver name (a sweep does not know the driver yet); same set as measure_sweep_tokens.py
 "is_fact": _yn("Does `quote` state a fact about the company?", "It states something that is true or planned for the company.", "It is boilerplate, a disclaimer, a heading or a bare mention."),
 "is_forecast": _yn("Does `quote` give the company's own forecast or outlook?", "The company itself says what it expects or targets.", "It reports what happened, or the forecast is someone else's."),
 "vs_expectation": _yn("Does `quote` compare a result or forecast with an outside expectation such as the consensus?", "It compares with analysts or another outside party.", "No such comparison."),
 "has_number": _yn("Does `quote` state a number or an amount?", "It gives a number, an amount or a percentage.", "It gives none."),
 "kind": {"type": "choice", "instructions": {"question": "Which kind of fact does `quote` state?", "read": READ_S}, "criteria": {
   "metric": {"what": "A standing level that can be read again."}, "guidance": {"what": "The company's own forecast."},
   "surprise": {"what": "A result compared with an outside expectation."}, "action_event": {"what": "A one-time happening."}, "none": {"what": "No fact."}}}}

def make_state(units, i, where):
    n, j, before = 0, i - 1, []
    while j >= 0 and n + len(units[j]) + 1 <= 520: before.insert(0, units[j]); n += len(units[j]) + 1; j -= 1
    if not before and i > 0: before = [units[i - 1]]
    n, j, after = 0, i + 1, []
    while j < len(units) and n + len(units[j]) + 1 <= 260: after.append(units[j]); n += len(units[j]) + 1; j += 1
    return {"where_it_appears": where, "text_before_quote": " ".join(before), "quote": units[i], "text_after_quote": " ".join(after)}

def tokens_stage(per_group=35, per_group_A=12):
    import prompts_v3 as P
    from card_prompts import STATE, UNIT_LEVEL, TIMETYPE
    from more_prompts import BASELINE
    from concurrent.futures import ThreadPoolExecutor
    out = pickle.load(open(PKL, "rb"))
    SET_A = {"fact_type": json.load(open("V6.json")), **STATE, **UNIT_LEVEL, **TIMETYPE, **BASELINE}
    groups = collections.defaultdict(list)
    for st, recs in out: groups[st["group"]].append((st, recs))
    jobs = []      # (group, state, use_A)
    for g, lst in groups.items():
        if g == "news titles": continue
        w = [s["est_calls"] for s, _ in lst]
        pool = [[(r["units"], i) for r in recs for i in range(len(r["units"]))] for _, recs in lst]
        for k in range(per_group):
            si = random.choices(range(len(lst)), weights=w)[0]
            units, i = random.choice(pool[si])
            jobs.append((g, make_state(units, i, WHERE[g]), k < per_group_A))
    drv = connect()
    with drv.session(default_access_mode="READ") as s:
        titles = [r["t"] for r in s.run("MATCH (n:News) WHERE size(coalesce(n.title,''))>0 WITH n, rand() AS r ORDER BY r LIMIT $k RETURN n.title AS t", k=per_group).data()]
    for k, t in enumerate(titles): jobs.append(("news titles", {"where_it_appears": WHERE["news titles"], "text_before_quote": "", "quote": t, "text_after_quote": ""}, k < per_group_A))
    def one(j):
        g, st, useA = j; assert "quote" in st
        rb = P.call(st, SET_B); ra = P.call(st, SET_A) if useA else None
        ch = sum(len(v) for v in st.values())
        return g, ch, rb["usage"]["input_tokens"] if "usage" in rb else None, ra["usage"]["input_tokens"] if ra and "usage" in ra else None
    with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
    res = collections.defaultdict(lambda: dict(B=[], A=[], ch=[]))
    for g, ch, tb, ta in R:
        if tb is not None: res[g]["B"].append(tb); res[g]["ch"].append(ch)
        if ta is not None and tb is not None: res[g]["A"].append(ta - tb)
    calls = collections.defaultdict(lambda: [0.0, 0.0, 0.0])          # est, lo, hi (summed over strata)
    for s, _ in out:
        g = s["group"]; calls[g][0] += s["est_calls"]; calls[g][1] += s["est_calls_ci"][0]; calls[g][2] += s["est_calls_ci"][1]
    dA = [d for r in res.values() for d in r["A"]]
    delta = statistics.mean(dA)
    allB = [(c, t) for r in res.values() for c, t in zip(r["ch"], r["B"])]
    xs, ys = [c for c, _ in allB], [t for _, t in allB]; mx, my = statistics.mean(xs), statistics.mean(ys)
    b = sum((x - mx) * (y - my) for x, y in allB) / sum((x - mx) ** 2 for x in xs); a = my - b * mx
    print(f"tokens = {a:.0f} + {b:.3f} x state characters   (1 token per {1/b:.1f} characters; {a:.0f} = questions + fixed part)   | A minus B = {delta:.0f} tokens (n={len(dA)}, sd {statistics.pstdev(dA):.0f})")
    print(f"measurement cost ${sum(sum(r['B']) for r in res.values())*PRICE + sum(sum(r['B'])+0 for r in res.values())*0:.3f} (B) + A on {len(dA)} calls")
    summary = {}
    print(f"\n{'group':24s} {'calls M (95%)':>22s} {'tokens/call B':>14s} {'A':>7s} {'state chars':>11s}")
    for g in calls:
        tb = res[g]["B"]; mB = statistics.mean(tb); sB = statistics.stdev(tb) / len(tb) ** 0.5
        summary[g] = dict(calls=calls[g], tokB=mB, tokB_se=sB, n=len(tb), chars=statistics.mean(res[g]["ch"]))
        print(f"{g:24s} {calls[g][0]/1e6:6.2f} [{calls[g][1]/1e6:5.2f}-{calls[g][2]/1e6:5.2f}] {mB:10.0f} ±{sB:3.0f} {mB+delta:7.0f} {summary[g]['chars']:11.0f}")
    json.dump(dict(groups=summary, delta=delta, a=a, b=b), open("sweep_tokens_stats.json", "w"), indent=1)
    # ---- Monte Carlo totals
    SCOPES = {"filings, sections only (10-K, 10-Q, 8-K + amendments)": ["prose sections", "FS sections"],
              "  + exhibits and filing-text-only (all filings)": ["prose sections", "FS sections", "press release exhibits", "contract exhibits", "filing text only"],
              "  all filings without contract exhibits (EX-10)": ["prose sections", "FS sections", "press release exhibits", "filing text only"],
              "  + transcripts (prepared remarks + Q&A)": ["prose sections", "FS sections", "press release exhibits", "contract exhibits", "filing text only", "prepared remarks", "Q&A"],
              "  + news (bodies + titles) = EVERYTHING": list(calls)}
    def draw(gs, useA):
        c = t = 0.0; cost = 0.0
        for g in gs:
            est, lo, hi = summary[g]["calls"]; sd = (hi - lo) / 3.92
            n = max(0.0, random.gauss(est, sd)); mB = random.gauss(summary[g]["tokB"], summary[g]["tokB_se"]) + (delta if useA else 0)
            c += n; t += n * mB
        return c, t * PRICE
    print("\n=== totals (5 questions in ONE call per unit)  median [95% interval]")
    print(f"{'scope':58s} {'calls':>16s} {'short tags $':>22s} {'full fact card $':>24s}")
    for name, gs in SCOPES.items():
        D = sorted(draw(gs, False) for _ in range(3000)); E = sorted(draw(gs, True) for _ in range(3000))
        f = lambda X, k: X[int(k * len(X))]
        print(f"{name:58s} {f(D,.5)[0]/1e6:6.1f}M [{f(D,.025)[0]/1e6:4.1f}-{f(D,.975)[0]/1e6:4.1f}] ${f(D,.5)[1]:7,.0f} [{f(D,.025)[1]:6,.0f}-{f(D,.975)[1]:6,.0f}]   ${f(E,.5)[1]:7,.0f} [{f(E,.025)[1]:6,.0f}-{f(E,.975)[1]:6,.0f}]")

def paragraph_stage(per_group=45, maxc=1200):
    """Paragraph-level sweep (needs SWEEP_PARA=1 stage 1, and the sentence-level stage 2 outputs). One call per paragraph chunk with the 5 short tags."""
    import prompts_v3 as P
    from concurrent.futures import ThreadPoolExecutor
    out = pickle.load(open(PKL_PARA, "rb")); base = json.load(open("sweep_tokens_stats.json")); delta = base["delta"]; a_fit, b_fit = base["a"], base["b"]
    sent_stats = json.load(open("sweep_units_stats.json")); sent_calls = collections.defaultdict(float)
    for s in sent_stats: sent_calls[s["group"]] += s["est_calls"]
    groups = collections.defaultdict(list)
    for st, recs in out: groups[st["group"]].append((st, recs))
    jobs = []
    for g, lst in groups.items():
        if g == "news titles": continue
        w = [s["para"][maxc]["est"] for s, _ in lst]; pool = [[c for r in recs for c in r["paras"][maxc]] for _, recs in lst]
        for _ in range(per_group):
            si = random.choices(range(len(lst)), weights=w)[0]; text, nu = random.choice(pool[si])
            jobs.append((g, {"where_it_appears": WHERE[g], "text_before_quote": "", "quote": text, "text_after_quote": ""}, nu))
    def one(j):
        g, st, nu = j; r = P.call(st, SET_B); a = r["answers"]
        return g, len(st["quote"]), r["usage"]["input_tokens"], nu, (a["is_fact"]["noul"] >= 0.5 or a["kind"]["choice"] != "none")
    with ThreadPoolExecutor(8) as ex: R = list(ex.map(one, jobs))
    res = collections.defaultdict(list)
    for g, ch, tok, nu, fl in R: res[g].append((ch, tok, nu, fl))
    chunks = collections.defaultdict(lambda: [0.0, 0.0, 0.0]); pstat = {}
    for s, _ in out:
        g = s["group"]
        if "para" in s:
            e = s["para"][maxc]; chunks[g][0] += e["est"]; chunks[g][1] += e["ci"][0]; chunks[g][2] += e["ci"][1]
        else: chunks[g] = [s["est_calls"]] * 3
    print(f"tokens spent measuring: {sum(t for rows in res.values() for _, t, _, _ in rows):,} = ${sum(t for rows in res.values() for _, t, _, _ in rows)*PRICE:.3f}")
    print(f"\n{'group':24s} {'chunks M':>9s} {'chars/chunk':>11s} {'sent/chunk':>10s} {'tokens/call':>12s} {'flagged chunks':>15s} {'flagged sentences':>18s}")
    summ = {}
    for g, rows in res.items():
        n = len(rows); tok = [t for _, t, _, _ in rows]; nu = [u for _, _, u, _ in rows]; fl = [f for _, _, _, f in rows]
        fs = sum(u for u, f in zip(nu, fl) if f) / sum(nu); fc = sum(fl) / n
        se_f = (fs * (1 - fs) / n) ** 0.5
        summ[g] = dict(chunks=chunks[g], tok=statistics.mean(tok), se=statistics.stdev(tok) / n ** 0.5, fs=fs, se_f=se_f, chars=statistics.mean([c for c, _, _, _ in rows]))
        print(f"{g:24s} {chunks[g][0]/1e6:9.2f} {summ[g]['chars']:11.0f} {statistics.mean(nu):10.1f} {summ[g]['tok']:9.0f} ±{summ[g]['se']:3.0f} {100*fc:14.0f}% {100*fs:17.0f}%")
    summ["news titles"] = dict(chunks=chunks["news titles"], tok=base["groups"]["news titles"]["tokB"], se=2, fs=summ["news bodies"]["fs"], se_f=summ["news bodies"]["se_f"], chars=78)
    sent_tok = {g: base["groups"][g]["tokB"] for g in base["groups"]}
    def draw(kind):
        tot = 0.0
        for g, s in summ.items():
            est, lo, hi = s["chunks"]; n = max(0.0, random.gauss(est, (hi - lo) / 3.92)); t = random.gauss(s["tok"], s["se"])
            f = min(1, max(0, random.gauss(s["fs"], s["se_f"])))
            if kind == "tags": tot += n * t
            elif kind == "card": tot += n * (t + delta)
            elif kind == "hybrid": tot += n * t + f * sent_calls[g] * (sent_tok[g] + delta)
        return tot * PRICE
    print("\n=== whole corpus, paragraph chunks up to %d characters (median [95%% interval])" % maxc)
    tc = sum(s["chunks"][0] for s in summ.values())
    print(f"chunks: {tc/1e6:.1f}M   (sentence units: {sum(sent_calls.values())/1e6:.1f}M)")
    for kind, label in (("tags", "paragraph tags only (5 short yes/no + kind)"), ("hybrid", "HYBRID: paragraph tags, then sentence-level full card on the flagged paragraphs"), ("card", "full card as ONE call per paragraph (one answer per paragraph: not valid for multi-fact paragraphs)")):
        D = sorted(draw(kind) for _ in range(3000)); print(f"  {label:96s} ${D[1500]:7,.0f}  [{D[75]:,.0f}-{D[2925]:,.0f}]")
    print("  (sentence level, from before: tags only $1,570 | full card $4,510)")
    print("\n=== sensitivity of the paragraph size (tags only; tokens = %.0f + %.3f x characters, the fit from the sentence run)" % (a_fit, b_fit))
    for m in (600, 1200, 2500):
        c = mc = 0.0
        for s, _ in out:
            if "para" in s: e = s["para"][m]; c += e["est"]; mc += e["est"] * (a_fit + b_fit * e["mean_chars"])
        c += 348670; mc += 348670 * 966
        print(f"  up to {m:4d} chars: {c/1e6:5.1f}M chunks, tags only ~${mc*PRICE:6,.0f}")

if __name__ == "__main__":
    if sys.argv[1:2] == ["paragraphs"]: paragraph_stage()
    if sys.argv[1:2] == ["units"]: units_stage()
    if sys.argv[1:2] == ["tokens"]: tokens_stage()
