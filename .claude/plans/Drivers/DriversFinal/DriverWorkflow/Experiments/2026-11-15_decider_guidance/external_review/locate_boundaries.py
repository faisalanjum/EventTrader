# Locate boundary test (15 Nov): percentages, dollar amounts, dates, names, companies, places next to punctuation,
# missing-fact cases, the 10 eval Locate requests (16-bit reference) and a 1,028-word report, through the live adapter.
# Usage: locate_boundaries.py <out json>   Compare two runs: locate_boundaries.py --compare <before> <after>
import json, sys, urllib.request
from pathlib import Path

A = "http://127.0.0.1:11435/api/decide"
T = Path(__file__).parent
P, D, DT, PE, CO, PL = "Percentages", "Dollar amounts", "Dates", "People", "Company names", "Places"
# (text, label, gold): gold = list of items, each a list of acceptable exact strings; [] = nothing should be found
CASES = [
    ("Acme Tools expects its operating margin for the current year to be 18.5%.", P, [["18.5%"]]),
    ("Revenue rose 12%, while costs fell 3%.", P, [["12%"], ["3%"]]),
    ("Gross margin was 41.2% (up from 39.8%).", P, [["41.2%"], ["39.8%"]]),
    ("Margin improved to 18.5%; costs fell.", P, [["18.5%"]]),
    ("Revenue rose 12% and costs fell 3% in the quarter.", P, [["12%"], ["3%"]]),
    ("The tax rate was 24.1 percent.", P, [["24.1 percent"]]),
    ("Same-store sales declined -2.5%.", P, [["-2.5%", "2.5%"]]),
    ("Organic growth was 7% (8% in constant currency).", P, [["7%"], ["8%"]]),
    ('"Margins of 30%" were cited by the CFO.', P, [["30%"]]),
    ("Return on equity reached **15.2%** in 2026.", P, [["15.2%"]]),
    ("Utilization: 88%", P, [["88%"]]),
    ("Interest rates rose 0.25%.\nThe bank kept its outlook.", P, [["0.25%"]]),
    ("Acme raised its revenue forecast to $120 million.", D, [["$120 million"]]),
    ("Net income was $4.2 billion, up from $3.9 billion.", D, [["$4.2 billion"], ["$3.9 billion"]]),
    ("The company recorded a loss ($3.1 million) in the quarter.", D, [["$3.1 million"]]),
    ("Earnings per share were $0.25.", D, [["$0.25"]]),
    ("It plans a US$5 billion buyback.", D, [["US$5 billion", "$5 billion"]]),
    ("Capital spending will be between $10 million and $12 million.", D, [["$10 million"], ["$12 million"]]),
    ("Sales reached €500 million.", D, [["€500 million"]]),
    ("Debt fell to £2.1 billion; cash rose.", D, [["£2.1 billion"]]),
    ("Revenue: $1.5 billion", D, [["$1.5 billion"]]),
    ("Dividends totaled **$300 million** in 2026.", D, [["$300 million"]]),
    ("The deal (valued at $2 billion) closed.", D, [["$2 billion"]]),
    ('"$50 million" was the figure quoted.', D, [["$50 million"]]),
    ("The quarter ended March 31, 2027.", DT, [["March 31, 2027"]]),
    ("Guidance for fiscal 2027, announced today, was raised.", DT, [["fiscal 2027", "2027"]]),
    ("Results for Q3 2026; outlook follows.", DT, [["Q3 2026"]]),
    ("The plan runs through 2028 (December 31, 2028).", DT, [["2028"], ["December 31, 2028"]]),
    ("Shares were issued on 15 January 2026.", DT, [["15 January 2026"]]),
    ("The meeting is on 2026-11-14.", DT, [["2026-11-14"]]),
    ('Payment is due "June 30, 2027".', DT, [["June 30, 2027"]]),
    ("Revenue grew in the first quarter of 2027.", DT, [["the first quarter of 2027", "first quarter of 2027"]]),
    ("CEO Jane Smith said margins would improve.", PE, [["Jane Smith"]]),
    ("The plan was approved by the CFO (John O'Neil).", PE, [["John O'Neil"]]),
    ('"We are pleased," said Mary Chen.', PE, [["Mary Chen"]]),
    ("Comments came from “Robert Brown”, the chair.", PE, [["Robert Brown"]]),
    ("Dr. Alan Wu; Ms. Priya Patel.", PE, [["Alan Wu", "Dr. Alan Wu"], ["Priya Patel", "Ms. Priya Patel"]]),
    ("The board thanked Sarah Lee.", PE, [["Sarah Lee"]]),
    ("(Thomas Green) will lead the division.", PE, [["Thomas Green"]]),
    ("Acme Tools Inc. reported results.", CO, [["Acme Tools Inc.", "Acme Tools Inc", "Acme Tools"]]),
    ("Shares of (Northwind Corp) rose.", CO, [["Northwind Corp"]]),
    ('"Contoso" agreed to buy Fabrikam, Inc.', CO, [["Contoso"], ["Fabrikam, Inc.", "Fabrikam, Inc", "Fabrikam"]]),
    ("The supplier, Globex, cut prices.", CO, [["Globex"]]),
    ("Revenue at Initech rose; Umbrella Corp fell.", CO, [["Initech"], ["Umbrella Corp"]]),
    ("The new factory is in Kingston, Ontario.", PL, [["Kingston, Ontario", "Kingston"]]),
    ("Sales in (Canada) grew.", PL, [["Canada"]]),
    ("Offices in “Toronto” and Paris.", PL, [["Toronto"], ["Paris"]]),
    ("It exited Brazil; Mexico remains.", PL, [["Brazil"], ["Mexico"]]),
    # missing facts: nothing should be found
    ("Acme Tools reviewed its warehouse procedures and delivery schedules.", P, []),
    ("Revenue rose 12%, while costs fell 3%.", "Dividend per share", []),
    ("The board met on Tuesday (no figures were discussed).", D, []),
    ("Margins were stable; no guidance was given.", P, []),
]


def call(state, questions):
    body = json.dumps({"model": "pplx-decider-v1.3:8bit", "state": state, "questions": questions}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(A, body, {"Content-Type": "application/json"}),
                                         timeout=1800))
    return {k: a["spans"] for k, a in r["answers"].items()}


def exact(state, spans):
    return all(state[s["start"]:s["end"]] == s["text"] for s in spans)


def run(out):
    res = {"cases": [], "eval": {}, "report": None, "all_exact": True}
    for text, label, gold in CASES:
        spans = call(text, {"x": {"type": "locate", "instructions": label}})["x"]
        found = {s["text"] for s in spans}
        hits = sum(any(g in found for g in item) for item in gold)
        extra = [t for t in found if not any(t in item for item in gold)]
        ok = exact(text, spans)
        res["all_exact"] &= ok
        res["cases"].append({"text": text, "label": label, "spans": spans, "hits": hits, "gold": len(gold),
                             "extra": extra, "exact_positions": ok})
        print(f"{hits}/{len(gold)} extra={extra} {label}: {text!r} -> {[s['text'] for s in spans]}", flush=True)
    ref = json.load(open(T / "4c_ref_answers.json"))
    for item in json.load(open(T / "eval_set.json")):
        if any(q.get("type") == "locate" for q in item["questions"].values()):
            got = call(item["state"], item["questions"])
            res["all_exact"] &= all(exact(item["state"], v) for v in got.values())
            res["eval"][item["id"]] = {k: {"spans": v, "same_as_16bit": [(s["start"], s["end"]) for s in v] == [
                (s["start"], s["end"]) for s in ref[item["id"]][k]["spans"]]} for k, v in got.items()}
    rep = json.load(open(T / "inputs_acme_report.json"))
    got = call(rep["state"], rep["questions"])
    res["all_exact"] &= all(exact(rep["state"], v) for v in got.values())
    res["report"] = {k: {"spans": v, "expected": [(s["start"], s["end"]) for s in rep["expected"][k]] == [
        (s["start"], s["end"]) for s in v]} for k, v in got.items()}
    res["summary"] = {"gold_hits": sum(c["hits"] for c in res["cases"]), "gold": sum(c["gold"] for c in res["cases"]),
                      "extra_spans": sum(len(c["extra"]) for c in res["cases"]),
                      "eval_same_as_16bit": sum(q["same_as_16bit"] for e in res["eval"].values() for q in e.values()),
                      "eval_questions": sum(len(e) for e in res["eval"].values()),
                      "report_expected": sum(q["expected"] for q in res["report"].values()),
                      "report_questions": len(res["report"]), "all_exact_positions": res["all_exact"]}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res["summary"]))


def compare(a, b):
    x, y = json.load(open(a)), json.load(open(b))
    print("before", json.dumps(x["summary"]), "\nafter ", json.dumps(y["summary"]))
    for c, d in zip(x["cases"], y["cases"], strict=True):
        if [(s["start"], s["end"]) for s in c["spans"]] != [(s["start"], s["end"]) for s in d["spans"]]:
            print(f"CHANGED {c['label']}: {c['text']!r}\n   before {[s['text'] for s in c['spans']]} ({c['hits']}/{c['gold']})"
                  f"\n   after  {[s['text'] for s in d['spans']]} ({d['hits']}/{d['gold']})")
    for name, part in (("eval", "eval"),):
        for k in x[part]:
            for q in x[part][k]:
                if x[part][k][q]["spans"] != y[part][k][q]["spans"]:
                    print(f"CHANGED eval {k}/{q}: {[s['text'] for s in x[part][k][q]['spans']]} -> "
                          f"{[s['text'] for s in y[part][k][q]['spans']]}")
    for q in x["report"]:
        print(f"report {q}: {[s['text'] for s in x['report'][q]['spans']]} -> {[s['text'] for s in y['report'][q]['spans']]}")


if __name__ == "__main__":
    compare(sys.argv[2], sys.argv[3]) if sys.argv[1] == "--compare" else run(sys.argv[1])
