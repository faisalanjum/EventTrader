"""Paragraph-level tag test (JEV.md §9): the plain variant P on (a) each known fact's surrounding text as a paragraph proxy (before + quote + after) and (b) random
paragraph chunks of the corpus (sweep_para_sample.pkl, chunks of up to 1,200 characters). Same five tags, `quote` = the whole paragraph.
Usage: /home/faisal/EventMarketDB/venv/bin/python3 run_tags_para.py  -> results_tags_para.json"""
import json, sys, pickle, random, collections, statistics
sys.path.insert(0, ".")
import prompts_v3 as P
import tag_prompts as T
from sweep_corpus import WHERE, PKL_PARA
from concurrent.futures import ThreadPoolExecutor
random.seed(51)
Q = T.variant("P")
pos = [p for p in json.load(open("items_tags_pos.json")) if p["type"] in ("metric", "guidance", "action_event", "surprise", "mixed")]
jobs = []
for p in pos:
    s = p["state"]; para = " ".join(x for x in (s["text_before_quote"], s["quote"], s["text_after_quote"]) if x).strip()
    jobs.append(("pos", p["id"], p["type"], dict(where_it_appears=s["where_it_appears"], text_before_quote="", quote=para, text_after_quote="")))
out = pickle.load(open(PKL_PARA, "rb")); groups = collections.defaultdict(list)
for st, recs in out: groups[st["group"]].append((st, recs))
for g, lst in groups.items():
    if g == "news titles": continue
    w = [s["para"][1200]["est"] for s, _ in lst]; pool = [[c for r in recs for c in r["paras"][1200]] for _, recs in lst]
    for k in range(45):
        si = random.choices(range(len(lst)), weights=w)[0]; text, nu = random.choice(pool[si])
        jobs.append(("rand", f"R|{g}|{k:02d}", g, dict(where_it_appears=WHERE[g], text_before_quote="", quote=text, text_after_quote="")))
def one(j):
    kind, iid, tag, st = j; assert "quote" in st
    r = P.call(st, Q); a = r["answers"]
    return kind, iid, tag, {q: a[q]["noul"] for q in T.ORDER}, r["usage"]["input_tokens"], len(st["quote"])
with ThreadPoolExecutor(12) as ex: R = list(ex.map(one, jobs))
json.dump(R, open("results_tags_para.json", "w"))
print(f"calls {len(R)} | mean tokens: known-fact paragraphs {statistics.mean(r[4] for r in R if r[0]=='pos'):.0f}, random chunks {statistics.mean(r[4] for r in R if r[0]=='rand'):.0f} | cost ${sum(r[4] for r in R)*0.042/1e6:.3f}")
